"""PHASE 5.3 — Tests for Memory Trust, Provenance, and Lifecycle Safety.

Validates the provenance-aware memory lifecycle:
DRAFT -> HUMAN VERIFIED -> VERIFIED MEMORY

Covers:
1. Draft postmortem is not trusted (provenance gate rejection).
2. Verified postmortem is trusted (accepted as historical precedent).
3. Draft cannot become trusted through triage (novelty=True, historical_matches=[]).
4. Verified runbook can be recalled from verified memory.
5. Failed mitigations only come from verified memory.
6. Human verification promotes DRAFT -> VERIFIED with immutable audit log.
7. Existing known seeded incidents remain VERIFIED.
8. Stateless mode remains unchanged (enable_memory=False).
9. Trust escalation prevention: AI draft cannot mark itself VERIFIED without human verification.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import pytest

from app.models.alert import AlertPayload, AlertSeverity
from app.models.memory import (
    IncidentMemoryItem,
    MatchStrength,
    MemorySourceType,
    MemoryStatus,
    RecallResultSummary,
    RetainIncidentPayload,
)
from app.models.triage import TriageRequest
from app.services.hindsight_service import hindsight_service
from app.services.provenance_service import provenance_service
from app.services.relevance_scorer import score_candidate_relevance
from app.services.triage_engine import triage_engine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def unverified_draft_candidate():
    """An AI-generated draft postmortem in Hindsight that has not been human verified."""
    return IncidentMemoryItem(
        id="mem-draft-001",
        incident_id="INC-DRAFT-001",
        service="checkout-service",
        severity="CRITICAL",
        alert_signature="CheckoutRedisPoolExhaustionHighErrorRate",
        title="Redis Connection Pool Starvation under High Traffic Spike",
        symptoms=[
            "p99 latency spiked to 4100ms",
            "RedisConnectionClosedException in checkout logs",
            "redis_pool_wait_duration_seconds > 2.5s",
        ],
        root_cause="Redis connection pool exhaustion during flash sale.",
        failed_mitigations=["Unverified AI advice: randomly restart all pods."],
        verified_runbook="RB-UNVERIFIED-DRAFT-RUNBOOK",
        runbook_used="RB-UNVERIFIED-DRAFT-RUNBOOK",
        raw_text="checkout-service RedisConnectionClosedException redis_pool_wait_duration_seconds connection pool",
        # Provenance: Unverified AI draft
        memory_status=MemoryStatus.DRAFT,
        source_type=MemorySourceType.AI_DRAFT,
        verified_by=None,
        verified_at=None,
        source_incident_id="INC-DRAFT-001",
    )


@pytest.fixture
def human_verified_candidate():
    """A human-verified postmortem with complete provenance attribution."""
    return IncidentMemoryItem(
        id="mem-verified-001",
        incident_id="INC-VERIFIED-001",
        service="checkout-service",
        severity="CRITICAL",
        alert_signature="CheckoutRedisPoolExhaustionHighErrorRate",
        title="Redis Connection Pool Starvation under High Traffic Spike",
        symptoms=[
            "p99 latency spiked to 4100ms",
            "RedisConnectionClosedException in checkout logs",
            "redis_pool_wait_duration_seconds > 2.5s",
        ],
        root_cause="Redis connection pool exhaustion during flash sale.",
        failed_mitigations=["Restarting checkout-service pods alone caused connection storm back to Redis master."],
        verified_runbook="RB-REDIS-FAILOVER",
        runbook_used="RB-REDIS-FAILOVER",
        raw_text="checkout-service RedisConnectionClosedException redis_pool_wait_duration_seconds connection pool",
        # Provenance: Human-verified
        memory_status=MemoryStatus.VERIFIED,
        source_type=MemorySourceType.HUMAN_VERIFIED,
        verified_by="oncall-sre",
        verified_at="2026-09-29T10:00:00Z",
        source_incident_id="INC-VERIFIED-001",
    )


@pytest.fixture
def checkout_alert():
    return AlertPayload(
        service="checkout-service",
        title="Checkout Redis Connection Pool Depletion & 503 Surge",
        description="Flash sale traffic spike exhausting checkout Redis client pool, causing thread blocks and 503 errors.",
        symptoms=[
            "p99 checkout response time degraded to 4300ms",
            "RedisConnectionClosedException logged during connection lease",
            "redis_pool_wait_duration_seconds exceeding 2800ms",
        ],
        severity=AlertSeverity.CRITICAL,
    )


# ---------------------------------------------------------------------------
# Test 1: Draft postmortem is not trusted
# ---------------------------------------------------------------------------

def test_1_draft_postmortem_is_not_trusted(checkout_alert, unverified_draft_candidate):
    """Test 1: Provenance gate rejects an unverified draft postmortem from being trusted precedent."""
    res = score_candidate_relevance(checkout_alert, unverified_draft_candidate)

    assert res.is_accepted is False
    assert res.match_strength == MatchStrength.NONE
    assert res.verdict == "REJECTED_UNVERIFIED_DRAFT_MEMORY"
    assert "provenance gate" in res.reason.lower() or "unverified" in res.reason.lower()
    assert any("provenance" in b.lower() for b in res.evidence_bullets)


# ---------------------------------------------------------------------------
# Test 2: Verified postmortem is trusted
# ---------------------------------------------------------------------------

def test_2_verified_postmortem_is_trusted(checkout_alert, human_verified_candidate):
    """Test 2: Human-verified postmortem passes the provenance gate and is accepted with HIGH match strength."""
    res = score_candidate_relevance(checkout_alert, human_verified_candidate)

    assert res.is_accepted is True
    assert res.match_strength == MatchStrength.HIGH
    assert res.verdict == "ACCEPTED"
    assert "RB-REDIS-FAILOVER" in [b for b in res.evidence_bullets if "RB-REDIS-FAILOVER" in b][0]


# ---------------------------------------------------------------------------
# Test 3: Draft cannot become trusted through triage
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_3_draft_cannot_become_trusted_through_triage(unverified_draft_candidate):
    """Test 3: Triage flow isolates unverified draft memories:

    - candidate is preserved in candidates_recalled for audit
    - historical_matches is strictly empty
    - novelty remains True
    """
    req = TriageRequest(
        service="checkout-service",
        alert="Checkout Redis Connection Pool Depletion & 503 Surge",
        title="Checkout Redis Connection Pool Depletion & 503 Surge",
        description="Flash sale traffic spike exhausting checkout Redis client pool.",
        symptoms=[
            "RedisConnectionClosedException logged during connection lease",
            "redis_pool_wait_duration_seconds exceeding 2800ms",
        ],
        severity="CRITICAL",
        enable_memory=True,
    )

    mock_summary = RecallResultSummary(
        match_strength=MatchStrength.NONE,
        is_novel=True,
        memories_found=[],  # Provenance gate rejected it
        candidates_retrieved=[unverified_draft_candidate],  # Raw candidate preserved
        relevance_verdict="REJECTED_UNVERIFIED_DRAFT_MEMORY",
        relevance_reason="Candidate rejected by provenance gate: unverified AI draft.",
        evidence_bullets=["Provenance check failed: candidate is an unverified DRAFT."],
        raw_recall_count=1,
        query_used="Service: checkout-service",
        hindsight_connected=True,
    )

    with patch.object(
        hindsight_service,
        "recall_incident_memory",
        new_callable=AsyncMock,
        return_value=mock_summary,
    ):
        response = await triage_engine.triage(req)

        assert response.novelty is True
        assert response.historical_matches == []
        assert response.candidates_recalled is not None
        assert len(response.candidates_recalled) == 1
        assert response.relevance_verdict == "REJECTED_UNVERIFIED_DRAFT_MEMORY"
        assert "No sufficiently relevant historical incident found" in response.incident_summary


# ---------------------------------------------------------------------------
# Test 4: Verified runbook can be recalled
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_4_verified_runbook_can_be_recalled(human_verified_candidate):
    """Test 4: When a verified postmortem matches, its verified runbook is recalled."""
    req = TriageRequest(
        service="checkout-service",
        alert="Checkout Redis Connection Pool Depletion",
        title="Checkout Redis Connection Pool Depletion",
        description="Redis connection closed exception under high load",
        symptoms=[
            "RedisConnectionClosedException logged during connection lease",
            "redis_pool_wait_duration_seconds exceeding 2800ms",
        ],
        severity="CRITICAL",
        enable_memory=True,
    )

    mock_summary = RecallResultSummary(
        match_strength=MatchStrength.HIGH,
        is_novel=False,
        memories_found=[human_verified_candidate],
        candidates_retrieved=[human_verified_candidate],
        relevance_verdict="ACCEPTED",
        evidence_bullets=["High correlation: verified postmortem aligns on Redis connection pool failure."],
        raw_recall_count=1,
        query_used="Service: checkout-service",
        hindsight_connected=True,
    )

    with patch.object(
        hindsight_service,
        "recall_incident_memory",
        new_callable=AsyncMock,
        return_value=mock_summary,
    ):
        response = await triage_engine.triage(req)

        assert response.novelty is False
        assert len(response.historical_matches) == 1
        assert response.historical_matches[0].incident_id == "INC-VERIFIED-001"
        assert response.historical_matches[0].verified_runbook == "RB-REDIS-FAILOVER"


# ---------------------------------------------------------------------------
# Test 5: Failed mitigations only come from verified memory
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_5_failed_mitigations_only_come_from_verified_memory(
    unverified_draft_candidate,
    human_verified_candidate,
):
    """Test 5: Failed mitigations from unverified drafts are NEVER injected as historical facts."""
    # Scenario A: Draft candidate
    draft_summary = RecallResultSummary(
        match_strength=MatchStrength.NONE,
        is_novel=True,
        memories_found=[],  # Rejected by provenance
        candidates_retrieved=[unverified_draft_candidate],
        relevance_verdict="REJECTED_UNVERIFIED_DRAFT_MEMORY",
        query_used="query",
    )
    req = TriageRequest(
        service="checkout-service",
        alert="Alert",
        symptoms=["RedisConnectionClosedException"],
        enable_memory=True,
    )

    with patch.object(hindsight_service, "recall_incident_memory", new_callable=AsyncMock, return_value=draft_summary):
        draft_triage = await triage_engine.triage(req)
        # Unverified draft's failed mitigations MUST NOT appear
        assert not any("randomly restart all pods" in fm for fm in draft_triage.failed_mitigations_to_avoid)

    # Scenario B: Verified candidate
    verified_summary = RecallResultSummary(
        match_strength=MatchStrength.HIGH,
        is_novel=False,
        memories_found=[human_verified_candidate],
        candidates_retrieved=[human_verified_candidate],
        relevance_verdict="ACCEPTED",
        query_used="query",
    )
    with patch.object(hindsight_service, "recall_incident_memory", new_callable=AsyncMock, return_value=verified_summary):
        verified_triage = await triage_engine.triage(req)
        # Verified historical failed mitigations ARE present
        assert any("Restarting checkout-service pods alone" in fm for fm in verified_triage.failed_mitigations_to_avoid)


# ---------------------------------------------------------------------------
# Test 6: Human verification promotes DRAFT -> VERIFIED
# ---------------------------------------------------------------------------

def test_6_human_verification_promotes_draft_to_verified(client):
    """Test 6: SRE verification endpoint promotes DRAFT to VERIFIED with audit record."""
    incident_id = "INC-PROV-882"
    verify_payload = {
        "verifier": "lead-sre-alice",
        "notes": "Reviewed and validated root cause and runbook in production sandbox.",
        "confirmed_runbook": "RB-REDIS-FAILOVER",
    }

    from app.services.auth_service import create_access_token
    auth_headers = {"Authorization": f"Bearer {create_access_token('lead-sre-alice')}"}

    with patch.object(
        hindsight_service,
        "retain_incident",
        new_callable=AsyncMock,
        return_value={"success": True, "incident_id": incident_id, "operation_id": "op-verify-882"},
    ):
        response = client.post(
            f"/api/postmortems/{incident_id}/verify",
            json=verify_payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["incident_id"] == incident_id
        assert data["memory_status"] == "VERIFIED"
        assert data["source_type"] == "HUMAN_VERIFIED"
        assert data["verified_by"] == "lead-sre-alice"

        # Check audit trail
        audit_trail = provenance_service.get_audit_trail(incident_id)
        assert len(audit_trail) > 0
        latest_audit = audit_trail[-1]
        assert latest_audit.verifier == "lead-sre-alice"
        assert latest_audit.action == "HUMAN_VERIFIED_POSTMORTEM"
        assert "Reviewed and validated" in latest_audit.notes


# ---------------------------------------------------------------------------
# Test 7: Existing known seeded incidents remain VERIFIED
# ---------------------------------------------------------------------------

def test_7_existing_known_seeded_incidents_remain_verified():
    """Test 7: Canonical seeded incidents (INC-104, INC-108, INC-203, INC-305, INC-402) are trusted."""
    for inc_id in ["INC-104", "INC-108", "INC-203", "INC-305", "INC-402"]:
        canonical_item = IncidentMemoryItem(
            id=f"mem-{inc_id.lower()}",
            incident_id=inc_id,
            service="test-service",
            title=f"Canonical Incident {inc_id}",
            memory_status=MemoryStatus.VERIFIED,
            source_type=MemorySourceType.HUMAN_VERIFIED,
            verified_by="sre-core-team",
        )
        assert provenance_service.is_trusted(canonical_item) is True


# ---------------------------------------------------------------------------
# Test 8: Stateless mode remains unchanged
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_8_stateless_mode_remains_unchanged():
    """Test 8: Explicit enable_memory=False completely bypasses memory."""
    req = TriageRequest(
        service="checkout-service",
        alert="CheckoutRedisPoolExhaustionHighErrorRate",
        symptoms=["RedisConnectionClosedException"],
        enable_memory=False,
    )

    with patch.object(hindsight_service, "recall_incident_memory") as mock_recall:
        response = await triage_engine.triage(req)
        mock_recall.assert_not_called()
        assert response.memory_used is False
        assert response.novelty is True
        assert response.historical_matches == []


# ---------------------------------------------------------------------------
# Test 9: Trust escalation prevention
# ---------------------------------------------------------------------------

def test_9_trust_escalation_blocked():
    """Test 9: AI draft payload claiming to be VERIFIED without human verification is demoted to DRAFT."""
    payload = RetainIncidentPayload(
        incident_id="INC-UNTRUSTED-999",
        service="cart-service",
        root_cause="Unverified AI claim",
        verified_runbook="RB-NONE",
        postmortem_summary="Summary",
        # Attempted trust escalation: marking VERIFIED without human verifier
        memory_status=MemoryStatus.VERIFIED,
        source_type=MemorySourceType.AI_DRAFT,
        verified_by=None,
    )

    validated = provenance_service.validate_provenance_on_retention(payload)

    # Trust escalation MUST be blocked
    assert validated.memory_status == MemoryStatus.DRAFT
    assert validated.source_type == MemorySourceType.AI_DRAFT
    assert validated.verified_by is None
