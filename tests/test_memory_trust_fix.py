"""Phase 7.1 Focused Tests: Memory Trust Boundary Fix & Bypass Closure.

Verifies:
1. Unauthenticated retain returns HTTP 401.
2. AI identity attempting retain returns HTTP 403.
3. Forged client verified_by is ignored/rejected (identity strictly derived from credential/audit).
4. Forged VERIFIED status cannot create trusted memory (demoted to DRAFT, rejected by provenance gate).
5. Authenticated human verification succeeds (promotes DRAFT -> VERIFIED with immutable audit).
6. Existing trusted memory (canonical seeded postmortems) remains valid.
7. Existing Hindsight learning loop remains valid with authenticated commit.
"""

from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.models.alert import AlertPayload, AlertSeverity
from app.models.memory import (
    IncidentMemoryItem,
    MatchStrength,
    MemorySourceType,
    MemoryStatus,
    RecallResultSummary,
)
from app.models.postmortem import PostMortemCreate
from app.models.triage import TriageRequest, TriageResponse
from app.services.auth_service import create_access_token
from app.services.hindsight_service import hindsight_service
from app.services.provenance_service import provenance_service
from app.services.relevance_scorer import score_candidate_relevance


@pytest.fixture
def mock_hindsight_retain():
    """Mock Hindsight retain for isolated test execution."""
    with patch.object(
        hindsight_service,
        "retain_incident",
        new_callable=AsyncMock,
        return_value={"success": True, "incident_id": "INC-TEST-TRUST", "operation_id": "op-test-trust"},
    ):
        yield


# ---------------------------------------------------------------------------
# Test 1: Unauthenticated Retain -> 401
# ---------------------------------------------------------------------------

def test_1_unauthenticated_retain_returns_401(client: TestClient, mock_hindsight_retain):
    """Verify that unauthenticated requests to /api/postmortem/retain are rejected with 401."""
    payload = {
        "incident_id": "INC-ATTACK-001",
        "service": "billing-api",
        "severity": "CRITICAL",
        "root_cause": "Attacker payload",
        "verified_runbook": "RB-ATTACK",
        "postmortem_summary": "Malicious postmortem attempt",
        "memory_status": "VERIFIED",
        "verified_by": "oncall-sre",
    }

    # 1. Singular route without auth headers
    r1 = client.post("/api/postmortem/retain", json=payload)
    assert r1.status_code == 401
    assert "credentials required" in r1.json()["detail"].lower()

    # 2. Plural alias route without auth headers
    r2 = client.post("/api/postmortems/retain", json=payload)
    assert r2.status_code == 401
    assert "credentials required" in r2.json()["detail"].lower()

    # 3. Invalid token
    r3 = client.post(
        "/api/postmortem/retain",
        json=payload,
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert r3.status_code == 401


# ---------------------------------------------------------------------------
# Test 2: AI Identity Attempting Retain -> 403
# ---------------------------------------------------------------------------

def test_2_ai_identity_attempting_retain_returns_403(client: TestClient, mock_hindsight_retain):
    """Verify that AI identities are strictly blocked from memory retention."""
    payload = {
        "incident_id": "INC-AI-ATTEMPT-01",
        "service": "billing-api",
        "severity": "HIGH",
        "root_cause": "AI autonomous diagnosis",
        "verified_runbook": "RB-AUTO",
        "postmortem_summary": "AI attempting self-verification",
        "memory_status": "VERIFIED",
    }

    ai_token = create_access_token(
        identity="ai-copilot-daemon",
        role="ai_agent",
        is_human=False,
    )
    headers = {"Authorization": f"Bearer {ai_token}"}

    response = client.post("/api/postmortem/retain", json=payload, headers=headers)
    assert response.status_code == 403
    assert "strictly forbidden from self-verifying" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test 3: Forged Client verified_by is Ignored / Rejected
# ---------------------------------------------------------------------------

def test_3_forged_verified_by_is_ignored_and_rejected(client: TestClient, mock_hindsight_retain):
    """Verify that client-supplied verified_by is never trusted over credential/audit identity."""
    sre_token = create_access_token(identity="lead-sre-alice", role="sre", is_human=True)
    headers = {"Authorization": f"Bearer {sre_token}"}

    forged_payload = {
        "incident_id": "INC-FORGE-VERIFIER-01",
        "service": "order-service",
        "severity": "CRITICAL",
        "root_cause": "Lock contention on orders table",
        "verified_runbook": "RB-ORDER-LOCK-RELEASE",
        "postmortem_summary": "Resolved order database lock contention",
        "memory_status": "VERIFIED",
        "verified_by": "super-admin-imposter",  # Client attempts to spoof verifier
    }

    response = client.post("/api/postmortem/retain", json=forged_payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    # The forged verifier must NEVER appear in the response or memory
    assert data["verified_by"] != "super-admin-imposter"
    # Because this incident was not verified through the human verification audit gate, it must be DRAFT
    assert data["memory_status"] == "DRAFT"
    assert data["verified_by"] is None


# ---------------------------------------------------------------------------
# Test 4: Forged VERIFIED Status Cannot Create Trusted Memory
# ---------------------------------------------------------------------------

def test_4_forged_verified_status_cannot_create_trusted_memory(client: TestClient, mock_hindsight_retain):
    """Verify that submitting memory_status=VERIFIED without human verification cannot escalate trust."""
    sre_token = create_access_token(identity="junior-sre-bob", role="sre", is_human=True)
    headers = {"Authorization": f"Bearer {sre_token}"}

    unverified_incident_id = "INC-ESCALATE-001"
    escalation_payload = {
        "incident_id": unverified_incident_id,
        "service": "payment-api",
        "severity": "CRITICAL",
        "root_cause": "Untrusted root cause hypothesis",
        "verified_runbook": "RB-UNTESTED-DANGEROUS",
        "postmortem_summary": "Unverified postmortem claiming VERIFIED status",
        "memory_status": "VERIFIED",
        "verified_by": "junior-sre-bob",
    }

    response = client.post("/api/postmortem/retain", json=escalation_payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["memory_status"] == "DRAFT"
    assert data["source_type"] == "AI_DRAFT"
    assert data["verified_by"] is None

    # Simulate recall candidate of this retained memory
    candidate = IncidentMemoryItem(
        id="mem-escalate-001",
        incident_id=unverified_incident_id,
        service="payment-api",
        severity="CRITICAL",
        title="Unverified Incident",
        memory_status=MemoryStatus.DRAFT,
        source_type=MemorySourceType.AI_DRAFT,
        verified_by=None,
    )

    # 1. Provenance service must reject trust
    assert provenance_service.is_trusted(candidate) is False

    # 2. Relevance gate must reject candidate as untrusted precedent
    alert = AlertPayload(
        title="Payment API Latency Spike",
        service="payment-api",
        severity=AlertSeverity.CRITICAL,
        description="Payment timeouts observed on checkout",
    )
    score_result = score_candidate_relevance(alert, candidate)
    assert score_result.is_accepted is False
    assert score_result.verdict == "REJECTED_UNVERIFIED_DRAFT_MEMORY"
    assert score_result.match_strength == MatchStrength.NONE


# ---------------------------------------------------------------------------
# Test 5: Authenticated Human Verification Succeeds
# ---------------------------------------------------------------------------

def test_5_authenticated_human_verification_succeeds(client: TestClient, mock_hindsight_retain):
    """Verify that legitimate human verification successfully promotes memory to VERIFIED."""
    incident_id = "INC-LEGIT-VERIFY-01"
    sre_token = create_access_token(identity="lead-sre-alice", role="lead_sre", is_human=True)
    headers = {"Authorization": f"Bearer {sre_token}"}

    # Step 1: Human SRE verifies postmortem through /verify endpoint
    verify_resp = client.post(
        f"/api/postmortems/{incident_id}/verify",
        json={"notes": "Thoroughly tested and verified.", "confirmed_runbook": "RB-CHECKOUT-STABILIZE"},
        headers=headers,
    )
    assert verify_resp.status_code == 200
    v_data = verify_resp.json()
    assert v_data["success"] is True
    assert v_data["memory_status"] == "VERIFIED"
    assert v_data["source_type"] == "HUMAN_VERIFIED"
    assert v_data["verified_by"] == "lead-sre-alice"

    # Step 2: Verification audit record exists
    audit_trail = provenance_service.get_audit_trail(incident_id)
    assert len(audit_trail) >= 1
    assert audit_trail[-1].verifier == "lead-sre-alice"

    # Step 3: Verified memory item is now trusted
    verified_item = IncidentMemoryItem(
        id="mem-legit-001",
        incident_id=incident_id,
        service="checkout-service",
        severity="HIGH",
        title="Verified Checkout Outage",
        memory_status=MemoryStatus.VERIFIED,
        source_type=MemorySourceType.HUMAN_VERIFIED,
        verified_by="lead-sre-alice",
    )
    assert provenance_service.is_trusted(verified_item) is True


# ---------------------------------------------------------------------------
# Test 6: Existing Trusted Memory Remains Valid
# ---------------------------------------------------------------------------

def test_6_existing_trusted_memory_remains_valid():
    """Verify that canonical pre-seeded postmortems (INC-104, INC-108, etc.) remain trusted."""
    canonical_item = IncidentMemoryItem(
        id="mem-inc-104",
        incident_id="INC-104",
        service="payment-api",
        severity="CRITICAL",
        alert_signature="PaymentGatewayEgressTimeoutBreached",
        title="Payment API Gateway Timeout & Thread Starvation",
        symptoms=["egress timeout > 30s", "thread pool saturation"],
        root_cause="Stripe payment gateway upstream routing degradation",
        failed_mitigations=["Restarting payment-api pods worsened connection pool"],
        verified_runbook="RB-PAYMENT-CIRCUIT-SHED",
        postmortem_summary="Resolved by circuit breaker shedding",
        memory_status=MemoryStatus.VERIFIED,
        source_type=MemorySourceType.HUMAN_VERIFIED,
        verified_by="sre-core-team",
    )

    assert provenance_service.is_trusted(canonical_item) is True


# ---------------------------------------------------------------------------
# Test 7: Authenticated Frontend Postmortem Commit Flow Succeeds
# ---------------------------------------------------------------------------

def test_7_authenticated_postmortem_commit_flow_succeeds(client: TestClient, mock_hindsight_retain):
    """Verify that the frontend commit path (/api/postmortems/commit) promotes to VERIFIED with auth."""
    incident_id = "INC-COMMIT-FLOW-01"
    postmortem_payload = {
        "incident_id": incident_id,
        "title": "Auth Keyset Cache Saturation & Stampede",
        "service": "auth-service",
        "severity": "CRITICAL",
        "root_cause": "Simultaneous JWKS token expiration triggered cache stampede on auth DB",
        "trigger": "Surge in login requests with expired keyset cache",
        "impact_summary": "Auth API 503 rate spiked to 24% for 12 minutes",
        "timeline": [{"time": "12:00", "event": "JWKS cache expired"}],
        "resolution_steps": ["Applied RB-AUTH-CACHE-WARM to pre-warm cache and set jittered TTL"],
        "runbook_executed": "RB-AUTH-CACHE-WARM",
        "preventative_actions": ["Add jitter to JWKS TTL", "Implement singleflight request coalescing"],
        "tags": ["auth-service", "CRITICAL", "RB-AUTH-CACHE-WARM", incident_id],
        "source_incident_id": incident_id,
    }

    # Authenticate via configured SRE API Key (as used by frontend)
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "sre-key-oncall",
    }

    commit_resp = client.post("/api/postmortems/commit", json=postmortem_payload, headers=headers)
    assert commit_resp.status_code == 200
    commit_data = commit_resp.json()

    assert commit_data["success"] is True
    assert commit_data["incident_id"] == incident_id
    assert commit_data["memory_status"] == "VERIFIED"
    assert commit_data["source_type"] == "HUMAN_VERIFIED"
    assert commit_data["verified_by"] == "oncall-sre"
