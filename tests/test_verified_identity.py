"""Focused tests for Phase 6.3A Authentication and Verified Identity.

Covers:
1. Unauthenticated verification -> HTTP 401.
2. Invalid credential (malformed JWT or invalid API key) -> HTTP 401.
3. Valid credential (JWT and API key) -> verification succeeds (200).
4. Forged client verifier is ignored/rejected (identity strictly derived from credential).
5. Authenticated identity appears in verification audit trail.
6. AI cannot self-verify (AI tokens rejected with 403; unverified AI drafts demoted).
7. Existing provenance lifecycle integrity preserved.
"""

from unittest.mock import AsyncMock, patch
import pytest

from app.models.memory import (
    IncidentMemoryItem,
    MemorySourceType,
    MemoryStatus,
    RetainIncidentPayload,
)
from app.services.auth_service import create_access_token
from app.services.hindsight_service import hindsight_service
from app.services.provenance_service import provenance_service


@pytest.fixture
def mock_hindsight_retain():
    with patch.object(
        hindsight_service,
        "retain_incident",
        new_callable=AsyncMock,
        return_value={"success": True, "incident_id": "INC-TEST-AUTH", "operation_id": "op-test-auth"},
    ):
        yield


# ---------------------------------------------------------------------------
# Test 1: Unauthenticated Verification -> 401
# ---------------------------------------------------------------------------

def test_1_unauthenticated_verification_returns_401(client, mock_hindsight_retain):
    """Verify that requests without credentials return HTTP 401."""
    incident_id = "INC-AUTH-UNAUTH-01"
    payload = {
        "verifier": "unauthenticated-user",
        "notes": "Attempting verification without auth header",
    }

    # Verify endpoint without Authorization / X-API-Key
    response = client.post(f"/api/postmortems/{incident_id}/verify", json=payload)
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers
    assert "credentials required" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test 2: Invalid Credential -> 401
# ---------------------------------------------------------------------------

def test_2_invalid_credential_returns_401(client, mock_hindsight_retain):
    """Verify that malformed JWT or invalid API key returns HTTP 401."""
    incident_id = "INC-AUTH-INVALID-01"
    payload = {"notes": "Attempting verification with bad credentials"}

    # Part A: Malformed/tampered JWT
    bad_jwt_headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.tampered.token"}
    response = client.post(
        f"/api/postmortems/{incident_id}/verify",
        json=payload,
        headers=bad_jwt_headers,
    )
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()

    # Part B: Invalid API key
    bad_key_headers = {"X-API-Key": "bogus-api-key-9999"}
    response = client.post(
        f"/api/postmortems/{incident_id}/verify",
        json=payload,
        headers=bad_key_headers,
    )
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test 3: Valid Credential -> Verification Succeeds
# ---------------------------------------------------------------------------

def test_3_valid_credential_verification_succeeds(client, mock_hindsight_retain):
    """Verify that valid JWT or API key successfully verifies postmortem."""
    incident_id = "INC-AUTH-VALID-01"
    payload = {
        "notes": "Verified by human SRE operator.",
        "confirmed_runbook": "RB-PAYMENT-EGRESS-TIMEOUT",
    }

    # Part A: Valid JWT Bearer token
    alice_token = create_access_token(identity="lead-sre-alice", role="lead_sre")
    jwt_headers = {"Authorization": f"Bearer {alice_token}"}
    response_jwt = client.post(
        f"/api/postmortems/{incident_id}/verify",
        json=payload,
        headers=jwt_headers,
    )
    assert response_jwt.status_code == 200
    data_jwt = response_jwt.json()
    assert data_jwt["success"] is True
    assert data_jwt["memory_status"] == "VERIFIED"
    assert data_jwt["source_type"] == "HUMAN_VERIFIED"
    assert data_jwt["verified_by"] == "lead-sre-alice"

    # Part B: Valid SRE API Key
    incident_id_key = "INC-AUTH-VALID-02"
    key_headers = {"X-API-Key": "sre-key-oncall"}
    response_key = client.post(
        f"/api/postmortems/{incident_id_key}/verify",
        json=payload,
        headers=key_headers,
    )
    assert response_key.status_code == 200
    data_key = response_key.json()
    assert data_key["verified_by"] == "oncall-sre"


# ---------------------------------------------------------------------------
# Test 4: Forged Client verifier is Ignored
# ---------------------------------------------------------------------------

def test_4_forged_client_verifier_is_ignored(client, mock_hindsight_retain):
    """Verify that client-supplied verifier string is never trusted over credential identity."""
    incident_id = "INC-AUTH-FORGE-01"
    # Authenticate as Alice, but client body claims to be 'super-admin-impostor'
    alice_token = create_access_token(identity="lead-sre-alice", role="lead_sre")
    headers = {"Authorization": f"Bearer {alice_token}"}

    forged_payload = {
        "verifier": "super-admin-impostor",
        "notes": "Attempting to spoof verified_by identity",
        "confirmed_runbook": "RB-REDIS-FAILOVER",
    }

    response = client.post(
        f"/api/postmortems/{incident_id}/verify",
        json=forged_payload,
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()

    # The forged client string 'super-admin-impostor' MUST be ignored
    assert data["verified_by"] == "lead-sre-alice"
    assert data["verified_by"] != "super-admin-impostor"


# ---------------------------------------------------------------------------
# Test 5: Authenticated Identity Appears in Verification Audit
# ---------------------------------------------------------------------------

def test_5_authenticated_identity_appears_in_verification_audit(client, mock_hindsight_retain):
    """Verify that the immutable audit trail accurately records the authenticated operator."""
    incident_id = "INC-AUTH-AUDIT-01"
    bob_token = create_access_token(identity="senior-sre-bob", role="sre")
    headers = {"Authorization": f"Bearer {bob_token}"}

    payload = {
        "notes": "Audited failover procedure and connection pool settings.",
        "confirmed_runbook": "RB-POSTGRES-POOL-EXPAND",
    }

    response = client.post(
        f"/api/postmortems/{incident_id}/verify",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 200

    # Retrieve audit records
    audit_resp = client.get(f"/api/postmortems/audit?incident_id={incident_id}")
    assert audit_resp.status_code == 200
    audits = audit_resp.json()
    assert len(audits) >= 1

    latest_audit = audits[-1]
    assert latest_audit["incident_id"] == incident_id
    assert latest_audit["verifier"] == "senior-sre-bob"
    assert latest_audit["action"] == "HUMAN_VERIFIED_POSTMORTEM"
    assert "Audited failover procedure" in latest_audit["notes"]


# ---------------------------------------------------------------------------
# Test 6: AI Cannot Self-Verify
# ---------------------------------------------------------------------------

def test_6_ai_cannot_self_verify(client, mock_hindsight_retain):
    """Verify that AI agents are forbidden from self-verifying postmortems (HTTP 403)."""
    incident_id = "INC-AUTH-AI-BLOCK-01"
    payload = {"notes": "AI copilot attempting automated self-verification."}

    # Part A: Token issued to an AI agent / copilot identity
    ai_token = create_access_token(
        identity="ai-incidentops-copilot",
        role="ai_agent",
        is_human=False,
    )
    headers = {"Authorization": f"Bearer {ai_token}"}

    response = client.post(
        f"/api/postmortems/{incident_id}/verify",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 403
    assert "strictly forbidden from self-verifying" in response.json()["detail"].lower()

    # Part B: In memory retention pipeline, AI draft cannot mark itself VERIFIED
    unverified_ai_payload = RetainIncidentPayload(
        bank_id="sre-incidentops-production",
        incident_id=incident_id,
        service="billing-api",
        severity="HIGH",
        root_cause="Automated AI hypothesis",
        verified_runbook="RB-AUTOGEN",
        postmortem_summary="AI draft without human verification",
        memory_status=MemoryStatus.VERIFIED,  # Attempting trust escalation
        source_type=MemorySourceType.AI_DRAFT,
        verified_by=None,
    )
    validated = provenance_service.validate_provenance_on_retention(unverified_ai_payload)
    # Must be demoted to DRAFT
    assert validated.memory_status == MemoryStatus.DRAFT
    assert validated.source_type == MemorySourceType.AI_DRAFT
    assert validated.verified_by is None


# ---------------------------------------------------------------------------
# Test 7: Existing Provenance Lifecycle Tests Still Pass
# ---------------------------------------------------------------------------

def test_7_provenance_lifecycle_integrity(client, mock_hindsight_retain):
    """Verify complete DRAFT -> HUMAN VERIFIED -> VERIFIED lifecycle with authenticated SRE."""
    incident_id = "INC-AUTH-LIFECYCLE-01"

    # Step 1: Draft item is NOT trusted
    draft_item = IncidentMemoryItem(
        id="mem-auth-draft",
        incident_id=incident_id,
        service="auth-service",
        title="Draft Incident",
        memory_status=MemoryStatus.DRAFT,
        source_type=MemorySourceType.AI_DRAFT,
        verified_by=None,
    )
    assert provenance_service.is_trusted(draft_item) is False

    # Step 2: Human verification with valid authenticated token promotes to VERIFIED
    sre_token = create_access_token(identity="lead-sre-alice", role="lead_sre")
    verify_resp = client.post(
        f"/api/postmortems/{incident_id}/verify",
        json={"notes": "Human SRE review complete.", "confirmed_runbook": "RB-AUTH-OK"},
        headers={"Authorization": f"Bearer {sre_token}"},
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["memory_status"] == "VERIFIED"
    assert verify_resp.json()["verified_by"] == "lead-sre-alice"

    # Step 3: Verified memory item is now trusted
    verified_item = IncidentMemoryItem(
        id="mem-auth-verified",
        incident_id=incident_id,
        service="auth-service",
        title="Verified Incident",
        memory_status=MemoryStatus.VERIFIED,
        source_type=MemorySourceType.HUMAN_VERIFIED,
        verified_by="lead-sre-alice",
    )
    assert provenance_service.is_trusted(verified_item) is True
