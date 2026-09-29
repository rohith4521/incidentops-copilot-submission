"""PHASE 5.4 — Multi-Incident Continuous Learning Tests.

Validates that the system accumulates useful operational knowledge across multiple incidents:
- incident 1 becomes VERIFIED
- incident 2 becomes VERIFIED
- incident 3 becomes VERIFIED
- drafts never become trusted
- multiple verified memories coexist
- relevant memory is accepted
- unrelated same-service memory is rejected
- paraphrased memory is recalled
- novel incident remains novel
- failed mitigations come only from VERIFIED memories
- stateless mode remains unchanged
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List
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
# Fixtures & Test Scenario Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def multi_incident_scenarios() -> Dict[str, Any]:
    """Load the canonical multi-incident scenario dataset."""
    scenarios_path = Path(__file__).resolve().parent.parent / "app" / "data" / "multi_incident_scenarios.json"
    with open(scenarios_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_multi_incident_memory(multi_incident_scenarios):
    """Fixture providing an isolated in-memory memory bank adhering to production rules."""
    memory_bank: List[IncidentMemoryItem] = []

    async def mock_retain(payload: RetainIncidentPayload):
        validated = provenance_service.validate_provenance_on_retention(payload)
        v_at_str = (
            validated.verified_at.isoformat()
            if isinstance(validated.verified_at, datetime)
            else (str(validated.verified_at) if validated.verified_at else None)
        )
        item = IncidentMemoryItem(
            id=f"mem-{validated.incident_id.lower()}",
            incident_id=validated.incident_id,
            service=validated.service,
            severity=validated.severity,
            alert_signature=validated.alert_signature,
            title=validated.title or f"{validated.incident_id} - {validated.service}",
            symptoms=validated.symptoms,
            root_cause=validated.root_cause,
            failed_mitigations=validated.failed_mitigations,
            verified_runbook=validated.verified_runbook,
            runbook_used=validated.verified_runbook,
            postmortem_summary=validated.postmortem_summary,
            resolution=validated.resolution or validated.postmortem_summary,
            tags=validated.tags,
            raw_text=(
                f"{validated.service} {validated.root_cause} {validated.verified_runbook} "
                f"{' '.join(validated.symptoms)} {' '.join(validated.failed_mitigations)}"
            ),
            memory_status=validated.memory_status,
            source_type=validated.source_type,
            verified_by=validated.verified_by,
            verified_at=v_at_str,
            source_incident_id=validated.source_incident_id or validated.incident_id,
        )
        existing_idx = next((i for i, m in enumerate(memory_bank) if m.incident_id == validated.incident_id), None)
        if existing_idx is not None:
            memory_bank[existing_idx] = item
        else:
            memory_bank.append(item)

        return {
            "success": True,
            "bank_id": validated.bank_id or "sre-incidentops-production",
            "incident_id": validated.incident_id,
            "operation_id": f"op-retain-{validated.incident_id}",
            "status": "retained",
            "memory_status": item.memory_status.value if hasattr(item.memory_status, "value") else str(item.memory_status),
            "source_type": item.source_type.value if hasattr(item.source_type, "value") else str(item.source_type),
            "verified_by": item.verified_by,
        }

    async def mock_recall(alert: AlertPayload) -> RecallResultSummary:
        if not memory_bank:
            return RecallResultSummary(
                match_strength=MatchStrength.NONE,
                is_novel=True,
                memories_found=[],
                candidates_retrieved=[],
                evidence_bullets=[f"No historical incidents found in memory bank for service '{alert.service}'."],
                raw_recall_count=0,
                query_used=alert.title,
                hindsight_connected=True,
            )

        candidates = [
            m for m in memory_bank
            if (m.service and m.service.lower() == (alert.service or "").lower())
            or any(s.lower() in m.raw_text.lower() for s in alert.symptoms)
        ]

        if not candidates:
            return RecallResultSummary(
                match_strength=MatchStrength.NONE,
                is_novel=True,
                memories_found=[],
                candidates_retrieved=[],
                evidence_bullets=[f"No candidates retrieved matching service '{alert.service}'."],
                raw_recall_count=0,
                query_used=alert.title,
                hindsight_connected=True,
            )

        accepted_memories: List[IncidentMemoryItem] = []
        evidence_bullets: List[str] = []
        overall_strength = MatchStrength.NONE
        overall_verdict = "REJECTED_LOW_RELEVANCE"
        overall_reason = "No candidate met acceptance criteria."

        for cand in candidates:
            score = score_candidate_relevance(alert, cand)
            if score.is_accepted:
                accepted_memories.append(cand)
                evidence_bullets.extend(score.evidence_bullets)
                overall_strength = score.match_strength
                overall_verdict = score.verdict
                overall_reason = score.reason
                break
            else:
                overall_verdict = score.verdict
                overall_reason = score.reason
                evidence_bullets.extend(score.evidence_bullets)

        return RecallResultSummary(
            match_strength=overall_strength,
            is_novel=len(accepted_memories) == 0,
            memories_found=accepted_memories,
            candidates_retrieved=candidates,
            relevance_verdict=overall_verdict,
            relevance_reason=overall_reason,
            evidence_bullets=evidence_bullets,
            raw_recall_count=len(candidates),
            query_used=alert.title,
            hindsight_connected=True,
        )

    with patch.object(hindsight_service, "retain_incident", side_effect=mock_retain), \
         patch.object(hindsight_service, "recall_incident_memory", side_effect=mock_recall):
        yield memory_bank


# ---------------------------------------------------------------------------
# Test 1: Incident 1 becomes VERIFIED
# ---------------------------------------------------------------------------

def test_1_incident_1_becomes_verified(client, mock_multi_incident_memory, multi_incident_scenarios):
    """Test 1: Incident 1 (Billing Postgres Deadlock) starts as DRAFT and promotes to VERIFIED."""
    inc1 = multi_incident_scenarios["training_incidents"][0]
    incident_id = inc1["incident_id"]

    # Step A: Human verification endpoint promotes DRAFT -> VERIFIED
    from app.services.auth_service import create_access_token
    auth_headers = {"Authorization": f"Bearer {create_access_token('oncall-sre')}"}

    verify_resp = client.post(
        f"/api/postmortems/{incident_id}/verify",
        json={
            "verifier": "oncall-sre",
            "notes": "Verified deadlock resolution and row locking ordering in sandbox.",
            "confirmed_runbook": inc1["verified_runbook"],
        },
        headers=auth_headers,
    )
    assert verify_resp.status_code == 200
    v_data = verify_resp.json()
    assert v_data["success"] is True
    assert v_data["memory_status"] == "VERIFIED"
    assert v_data["source_type"] == "HUMAN_VERIFIED"
    assert v_data["verified_by"] == "oncall-sre"

    # Step B: Retain as verified memory
    payload = {
        "bank_id": "sre-incidentops-production",
        "incident_id": incident_id,
        "service": inc1["service"],
        "severity": inc1["severity"],
        "alert_signature": inc1["alert_signature"],
        "title": inc1["title"],
        "symptoms": inc1["symptoms"],
        "root_cause": inc1["root_cause"],
        "failed_mitigations": inc1["failed_mitigations"],
        "verified_runbook": inc1["verified_runbook"],
        "postmortem_summary": inc1["postmortem_summary"],
        "resolution": inc1["resolution"],
        "tags": inc1["tags"],
        "memory_status": "VERIFIED",
        "source_type": "HUMAN_VERIFIED",
        "verified_by": "oncall-sre",
    }
    retain_resp = client.post("/api/postmortem/retain", json=payload, headers=auth_headers)
    assert retain_resp.status_code == 200
    assert retain_resp.json()["memory_status"] == "VERIFIED"

    # Verify presence in memory bank
    assert len(mock_multi_incident_memory) == 1
    assert mock_multi_incident_memory[0].incident_id == incident_id
    assert mock_multi_incident_memory[0].memory_status == MemoryStatus.VERIFIED


# ---------------------------------------------------------------------------
# Test 2: Incident 2 becomes VERIFIED
# ---------------------------------------------------------------------------

def test_2_incident_2_becomes_verified(client, mock_multi_incident_memory, multi_incident_scenarios):
    """Test 2: Incident 2 (Stripe Gateway Timeout) on same service promotes to VERIFIED."""
    inc2 = multi_incident_scenarios["training_incidents"][1]
    incident_id = inc2["incident_id"]

    from app.services.auth_service import create_access_token
    auth_headers = {"Authorization": f"Bearer {create_access_token('oncall-sre')}"}

    verify_resp = client.post(
        f"/api/postmortems/{incident_id}/verify",
        json={
            "verifier": "oncall-sre",
            "notes": "Verified circuit breaker trip for outbound Stripe webhooks.",
            "confirmed_runbook": inc2["verified_runbook"],
        },
        headers=auth_headers,
    )
    assert verify_resp.status_code == 200
    v_data = verify_resp.json()
    assert v_data["memory_status"] == "VERIFIED"
    assert v_data["verified_by"] == "oncall-sre"

    payload = {
        "bank_id": "sre-incidentops-production",
        "incident_id": incident_id,
        "service": inc2["service"],
        "severity": inc2["severity"],
        "alert_signature": inc2["alert_signature"],
        "title": inc2["title"],
        "symptoms": inc2["symptoms"],
        "root_cause": inc2["root_cause"],
        "failed_mitigations": inc2["failed_mitigations"],
        "verified_runbook": inc2["verified_runbook"],
        "postmortem_summary": inc2["postmortem_summary"],
        "resolution": inc2["resolution"],
        "tags": inc2["tags"],
        "memory_status": "VERIFIED",
        "source_type": "HUMAN_VERIFIED",
        "verified_by": "oncall-sre",
    }
    retain_resp = client.post("/api/postmortem/retain", json=payload, headers=auth_headers)
    assert retain_resp.status_code == 200
    assert retain_resp.json()["memory_status"] == "VERIFIED"


# ---------------------------------------------------------------------------
# Test 3: Incident 3 becomes VERIFIED
# ---------------------------------------------------------------------------

def test_3_incident_3_becomes_verified(client, mock_multi_incident_memory, multi_incident_scenarios):
    """Test 3: Incident 3 (Auth JWT Cache Stampede) promotes to VERIFIED."""
    inc3 = multi_incident_scenarios["training_incidents"][2]
    incident_id = inc3["incident_id"]

    from app.services.auth_service import create_access_token
    auth_headers = {"Authorization": f"Bearer {create_access_token('oncall-sre')}"}

    verify_resp = client.post(
        f"/api/postmortems/{incident_id}/verify",
        json={
            "verifier": "oncall-sre",
            "notes": "Validated keyset cache warming and TTL jittering in auth cluster.",
            "confirmed_runbook": inc3["verified_runbook"],
        },
        headers=auth_headers,
    )
    assert verify_resp.status_code == 200
    v_data = verify_resp.json()
    assert v_data["memory_status"] == "VERIFIED"
    assert v_data["verified_by"] == "oncall-sre"

    payload = {
        "bank_id": "sre-incidentops-production",
        "incident_id": incident_id,
        "service": inc3["service"],
        "severity": inc3["severity"],
        "alert_signature": inc3["alert_signature"],
        "title": inc3["title"],
        "symptoms": inc3["symptoms"],
        "root_cause": inc3["root_cause"],
        "failed_mitigations": inc3["failed_mitigations"],
        "verified_runbook": inc3["verified_runbook"],
        "postmortem_summary": inc3["postmortem_summary"],
        "resolution": inc3["resolution"],
        "tags": inc3["tags"],
        "memory_status": "VERIFIED",
        "source_type": "HUMAN_VERIFIED",
        "verified_by": "oncall-sre",
    }
    retain_resp = client.post("/api/postmortem/retain", json=payload, headers=auth_headers)
    assert retain_resp.status_code == 200
    assert retain_resp.json()["memory_status"] == "VERIFIED"


# ---------------------------------------------------------------------------
# Test 4: Drafts never become trusted
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_4_drafts_never_become_trusted(mock_multi_incident_memory, multi_incident_scenarios):
    """Test 4: Unverified AI draft postmortem is rejected by provenance gate and never trusted."""
    inc6 = multi_incident_scenarios["training_incidents"][5]  # Search service draft
    draft_item = IncidentMemoryItem(
        id="mem-inc-seq-006",
        incident_id=inc6["incident_id"],
        service=inc6["service"],
        severity=inc6["severity"],
        title=inc6["title"],
        symptoms=inc6["symptoms"],
        root_cause=inc6["root_cause"],
        failed_mitigations=inc6["failed_mitigations"],
        verified_runbook=inc6["verified_runbook"],
        raw_text=f"{inc6['service']} {inc6['root_cause']} {' '.join(inc6['symptoms'])}",
        memory_status=MemoryStatus.DRAFT,
        source_type=MemorySourceType.AI_DRAFT,
        verified_by=None,
    )
    mock_multi_incident_memory.append(draft_item)

    alert = AlertPayload(
        service=inc6["service"],
        title="ElasticsearchFieldDataCacheOverflowAndGC",
        description="Search node circuit breaking exception on fielddata.",
        symptoms=inc6["symptoms"],
        severity=AlertSeverity.HIGH,
    )

    # 1. Relevance scorer unit check
    score = score_candidate_relevance(alert, draft_item)
    assert score.is_accepted is False
    assert score.match_strength == MatchStrength.NONE
    assert score.verdict == "REJECTED_UNVERIFIED_DRAFT_MEMORY"

    # 2. Triage engine integration check
    req = TriageRequest(
        service=inc6["service"],
        alert="ElasticsearchFieldDataCacheOverflowAndGC",
        title="ElasticsearchFieldDataCacheOverflowAndGC",
        symptoms=inc6["symptoms"],
        severity="HIGH",
        enable_memory=True,
    )
    resp = await triage_engine.triage(req)
    assert resp.novelty is True
    assert resp.historical_matches == []
    assert resp.relevance_verdict == "REJECTED_UNVERIFIED_DRAFT_MEMORY"


# ---------------------------------------------------------------------------
# Test 5: Multiple verified memories coexist
# ---------------------------------------------------------------------------

def test_5_multiple_verified_memories_coexist(mock_multi_incident_memory, multi_incident_scenarios):
    """Test 5: Multiple verified incidents across distinct services and patterns coexist in memory."""
    for inc in multi_incident_scenarios["training_incidents"]:
        if inc.get("should_verify"):
            item = IncidentMemoryItem(
                id=f"mem-{inc['incident_id'].lower()}",
                incident_id=inc["incident_id"],
                service=inc["service"],
                severity=inc["severity"],
                title=inc["title"],
                symptoms=inc["symptoms"],
                root_cause=inc["root_cause"],
                failed_mitigations=inc["failed_mitigations"],
                verified_runbook=inc["verified_runbook"],
                raw_text=f"{inc['service']} {inc['root_cause']} {inc['verified_runbook']} {' '.join(inc['symptoms'])}",
                memory_status=MemoryStatus.VERIFIED,
                source_type=MemorySourceType.HUMAN_VERIFIED,
                verified_by="oncall-sre",
                verified_at="2026-09-29T10:00:00Z",
            )
            mock_multi_incident_memory.append(item)

    # Verify 5 distinct verified memories coexist
    assert len(mock_multi_incident_memory) == 5
    ids = {m.incident_id for m in mock_multi_incident_memory}
    assert ids == {"INC-SEQ-001", "INC-SEQ-002", "INC-SEQ-003", "INC-SEQ-004", "INC-SEQ-005"}
    assert all(m.memory_status == MemoryStatus.VERIFIED for m in mock_multi_incident_memory)
    assert all(m.verified_by == "oncall-sre" for m in mock_multi_incident_memory)


# ---------------------------------------------------------------------------
# Test 6: Relevant memory is accepted
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_6_relevant_memory_is_accepted(mock_multi_incident_memory, multi_incident_scenarios):
    """Test 6: Repeating alert for Incident 2 (Stripe webhook timeout) recalls and accepts INC-SEQ-002."""
    inc2 = multi_incident_scenarios["training_incidents"][1]
    item2 = IncidentMemoryItem(
        id="mem-inc-seq-002",
        incident_id="INC-SEQ-002",
        service="billing-service",
        title=inc2["title"],
        symptoms=inc2["symptoms"],
        root_cause=inc2["root_cause"],
        failed_mitigations=inc2["failed_mitigations"],
        verified_runbook=inc2["verified_runbook"],
        raw_text=f"billing-service {inc2['root_cause']} {inc2['verified_runbook']} {' '.join(inc2['symptoms'])}",
        memory_status=MemoryStatus.VERIFIED,
        source_type=MemorySourceType.HUMAN_VERIFIED,
        verified_by="oncall-sre",
    )
    mock_multi_incident_memory.append(item2)

    req = TriageRequest(
        service="billing-service",
        alert="BillingStripeGatewayTimeoutCircuitOpenRepeat",
        title="Billing Stripe Gateway Timeout Repeat",
        symptoms=inc2["symptoms"],
        severity="CRITICAL",
        enable_memory=True,
    )
    resp = await triage_engine.triage(req)
    assert resp.novelty is False
    assert len(resp.historical_matches) == 1
    assert resp.historical_matches[0].incident_id == "INC-SEQ-002"
    assert resp.historical_matches[0].verified_runbook == "RB-GATEWAY-CIRCUIT-TRIP"
    assert resp.recommended_runbook.runbook_id == "RB-GATEWAY-CIRCUIT-TRIP"


# ---------------------------------------------------------------------------
# Test 7: Unrelated same-service memory is rejected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_7_unrelated_same_service_memory_is_rejected(mock_multi_incident_memory, multi_incident_scenarios):
    """Test 7: Billing container OOM alert rejects both INC-SEQ-001 (deadlock) and INC-SEQ-002 (timeout)."""
    # Seed both billing memories
    for idx in [0, 1]:
        inc = multi_incident_scenarios["training_incidents"][idx]
        item = IncidentMemoryItem(
            id=f"mem-{inc['incident_id'].lower()}",
            incident_id=inc["incident_id"],
            service="billing-service",
            title=inc["title"],
            symptoms=inc["symptoms"],
            root_cause=inc["root_cause"],
            failed_mitigations=inc["failed_mitigations"],
            verified_runbook=inc["verified_runbook"],
            raw_text=f"billing-service {inc['root_cause']} {inc['verified_runbook']} {' '.join(inc['symptoms'])}",
            memory_status=MemoryStatus.VERIFIED,
            source_type=MemorySourceType.HUMAN_VERIFIED,
            verified_by="oncall-sre",
        )
        mock_multi_incident_memory.append(item)

    # Ingest OOM alert for billing-service (different failure domain)
    oom_alert = multi_incident_scenarios["follow_up_evaluation_alerts"][2]
    req = TriageRequest(
        service="billing-service",
        alert=oom_alert["title"],
        title=oom_alert["title"],
        symptoms=oom_alert["symptoms"],
        severity="CRITICAL",
        enable_memory=True,
    )
    resp = await triage_engine.triage(req)
    assert resp.novelty is True
    assert resp.historical_matches == []
    assert resp.relevance_verdict in ("REJECTED_DIFFERENT_FAILURE_MODE", "REJECTED_LOW_RELEVANCE")


# ---------------------------------------------------------------------------
# Test 8: Paraphrased memory is recalled
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_8_paraphrased_memory_is_recalled(mock_multi_incident_memory, multi_incident_scenarios):
    """Test 8: Paraphrased catalog cache stampede correctly recalls and accepts INC-SEQ-004."""
    inc4 = multi_incident_scenarios["training_incidents"][3]
    item4 = IncidentMemoryItem(
        id="mem-inc-seq-004",
        incident_id="INC-SEQ-004",
        service="catalog-service",
        title=inc4["title"],
        symptoms=inc4["symptoms"],
        root_cause=inc4["root_cause"],
        failed_mitigations=inc4["failed_mitigations"],
        verified_runbook=inc4["verified_runbook"],
        raw_text=f"catalog-service {inc4['root_cause']} {inc4['verified_runbook']} {' '.join(inc4['symptoms'])}",
        memory_status=MemoryStatus.VERIFIED,
        source_type=MemorySourceType.HUMAN_VERIFIED,
        verified_by="oncall-sre",
    )
    mock_multi_incident_memory.append(item4)

    para_alert = multi_incident_scenarios["follow_up_evaluation_alerts"][3]
    req = TriageRequest(
        service="catalog-service",
        alert=para_alert["title"],
        title=para_alert["title"],
        symptoms=para_alert["symptoms"],
        severity="CRITICAL",
        enable_memory=True,
    )
    resp = await triage_engine.triage(req)
    assert resp.novelty is False
    assert len(resp.historical_matches) == 1
    assert resp.historical_matches[0].incident_id == "INC-SEQ-004"
    assert resp.historical_matches[0].verified_runbook == "RB-CATALOG-STAGGER-TTL"
    assert resp.recommended_runbook.runbook_id == "RB-CATALOG-STAGGER-TTL"


# ---------------------------------------------------------------------------
# Test 9: Novel incident remains novel
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_9_novel_incident_remains_novel(mock_multi_incident_memory, multi_incident_scenarios):
    """Test 9: Genuinely novel alert on unseen service (ml-inference-gateway) has novelty=True."""
    # Memory bank populated with other incidents
    for idx in range(3):
        inc = multi_incident_scenarios["training_incidents"][idx]
        mock_multi_incident_memory.append(
            IncidentMemoryItem(
                id=f"mem-{inc['incident_id'].lower()}",
                incident_id=inc["incident_id"],
                service=inc["service"],
                title=inc["title"],
                memory_status=MemoryStatus.VERIFIED,
                source_type=MemorySourceType.HUMAN_VERIFIED,
                verified_by="oncall-sre",
            )
        )

    novel_alert = multi_incident_scenarios["follow_up_evaluation_alerts"][4]
    req = TriageRequest(
        service="ml-inference-gateway",
        alert=novel_alert["title"],
        title=novel_alert["title"],
        symptoms=novel_alert["symptoms"],
        severity="CRITICAL",
        enable_memory=True,
    )
    resp = await triage_engine.triage(req)
    assert resp.novelty is True
    assert resp.historical_matches == []
    assert "No sufficiently relevant historical incident found" in resp.incident_summary


# ---------------------------------------------------------------------------
# Test 10: Failed mitigations come only from VERIFIED memories
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_10_failed_mitigations_come_only_from_verified_memories(
    mock_multi_incident_memory,
    multi_incident_scenarios,
):
    """Test 10: SRE is warned of anti-patterns only from human-verified incidents."""
    inc1 = multi_incident_scenarios["training_incidents"][0]
    verified_item = IncidentMemoryItem(
        id="mem-inc-seq-001",
        incident_id="INC-SEQ-001",
        service="billing-service",
        title=inc1["title"],
        symptoms=inc1["symptoms"],
        root_cause=inc1["root_cause"],
        failed_mitigations=["Dangerous action: do not increase worker concurrency."],
        verified_runbook=inc1["verified_runbook"],
        raw_text=f"billing-service {inc1['root_cause']} {inc1['verified_runbook']} {' '.join(inc1['symptoms'])}",
        memory_status=MemoryStatus.VERIFIED,
        source_type=MemorySourceType.HUMAN_VERIFIED,
        verified_by="oncall-sre",
    )
    mock_multi_incident_memory.append(verified_item)

    req = TriageRequest(
        service="billing-service",
        alert="BillingPostgresDeadlockTxRollbackRepeat",
        title="Billing Postgres Deadlock Repeat",
        symptoms=inc1["symptoms"],
        severity="CRITICAL",
        enable_memory=True,
    )
    resp = await triage_engine.triage(req)
    assert any("do not increase worker concurrency" in fm for fm in resp.failed_mitigations_to_avoid)


# ---------------------------------------------------------------------------
# Test 11: Stateless mode remains unchanged
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_11_stateless_mode_remains_unchanged(mock_multi_incident_memory, multi_incident_scenarios):
    """Test 11: Setting enable_memory=False completely bypasses accumulated memory bank."""
    inc1 = multi_incident_scenarios["training_incidents"][0]
    item1 = IncidentMemoryItem(
        id="mem-inc-seq-001",
        incident_id="INC-SEQ-001",
        service="billing-service",
        title=inc1["title"],
        symptoms=inc1["symptoms"],
        root_cause=inc1["root_cause"],
        failed_mitigations=inc1["failed_mitigations"],
        verified_runbook=inc1["verified_runbook"],
        raw_text=f"billing-service {inc1['root_cause']} {inc1['verified_runbook']} {' '.join(inc1['symptoms'])}",
        memory_status=MemoryStatus.VERIFIED,
        source_type=MemorySourceType.HUMAN_VERIFIED,
        verified_by="oncall-sre",
    )
    mock_multi_incident_memory.append(item1)

    req = TriageRequest(
        service="billing-service",
        alert="BillingPostgresDeadlockTxRollbackRepeat",
        title="Billing Postgres Deadlock Repeat",
        symptoms=inc1["symptoms"],
        severity="CRITICAL",
        enable_memory=False,  # Explicitly disabled
    )
    resp = await triage_engine.triage(req)
    assert resp.memory_used is False
    assert resp.novelty is True
    assert resp.historical_matches == []
    assert "Stateless" in resp.incident_summary
