"""PHASE 7.4B — Direct Memory Retention Protection Tests.

Validates:
1. Anonymous request to POST /api/memory/retain returns HTTP 401 Unauthorized.
2. AI identity attempting to call POST /api/memory/retain returns HTTP 403 Forbidden.
3. Authenticated human verifier (via JWT or SRE API key) is allowed to call POST /api/memory/retain.
4. Spoofed client-supplied verified_by is ignored/stripped when no prior human verification exists.
5. Spoofed client-supplied VERIFIED status is demoted to DRAFT when no prior human verification exists.
6. The endpoint is marked as deprecated in OpenAPI schema.
"""

from unittest.mock import AsyncMock, patch
import pytest
from starlette.testclient import TestClient

from app.config import settings
from app.main import app
from app.models.memory import MemorySourceType, MemoryStatus
from app.services.auth_service import create_access_token
from app.services.hindsight_service import hindsight_service
from app.services.provenance_service import provenance_service


@pytest.fixture
def client():
    """FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_audit_records():
    """Clear provenance audit records between tests."""
    with provenance_service._get_connection() as conn:
        conn.execute("DELETE FROM provenance_audit_records;")
        conn.commit()
    yield
    with provenance_service._get_connection() as conn:
        conn.execute("DELETE FROM provenance_audit_records;")
        conn.commit()


@pytest.fixture
def sample_payload():
    """Sample incident memory retention payload."""
    return {
        "incident_id": "INC-TEST-RETAIN-DIRECT",
        "service": "billing-service",
        "severity": "HIGH",
        "title": "Payment Gateway Timeout",
        "symptoms": ["HTTP 504 Gateway Timeout"],
        "root_cause": "Database connection pool exhausted",
        "verified_runbook": "RB-RESTART-POOL",
        "postmortem_summary": "Restarted connection pool to restore operations",
        "memory_status": "DRAFT",
    }


# ---------------------------------------------------------------------------
# Test 1: Anonymous retain returns HTTP 401 Unauthorized
# ---------------------------------------------------------------------------

def test_1_anonymous_retain_returns_401(client: TestClient, sample_payload):
    """Verify that unauthenticated requests to POST /api/memory/retain are rejected with HTTP 401."""
    response = client.post("/api/memory/retain", json=sample_payload)
    assert response.status_code == 401
    assert "Authentication credentials required" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Test 2: AI identity returns HTTP 403 Forbidden
# ---------------------------------------------------------------------------

def test_2_ai_identity_returns_403(client: TestClient, sample_payload):
    """Verify that AI agents attempting to call POST /api/memory/retain are rejected with HTTP 403."""
    # Generate token for an automated AI identity
    ai_token = create_access_token(identity="copilot-ai-agent", role="ai_agent", is_human=False)
    headers = {"Authorization": f"Bearer {ai_token}"}

    response = client.post("/api/memory/retain", json=sample_payload, headers=headers)
    assert response.status_code == 403
    assert "AI agents are strictly forbidden" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Test 3: Authenticated human verifier is allowed
# ---------------------------------------------------------------------------

def test_3_human_verifier_allowed(client: TestClient, sample_payload):
    """Verify that an authenticated human SRE can successfully call POST /api/memory/retain."""
    human_token = create_access_token(identity="lead-sre-alice", role="sre", is_human=True)
    headers = {"Authorization": f"Bearer {human_token}"}

    with patch.object(
        hindsight_service,
        "retain_incident",
        new_callable=AsyncMock,
        return_value={"success": True, "status": "retained", "operation_id": "op-test-direct-retain"},
    ) as mock_retain:
        response = client.post("/api/memory/retain", json=sample_payload, headers=headers)
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert mock_retain.called

    # Also verify with valid X-API-Key
    api_key_headers = {"X-API-Key": "sre-key-oncall"}
    with patch.object(
        hindsight_service,
        "retain_incident",
        new_callable=AsyncMock,
        return_value={"success": True, "status": "retained", "operation_id": "op-test-key-retain"},
    ):
        resp_key = client.post("/api/memory/retain", json=sample_payload, headers=api_key_headers)
        assert resp_key.status_code == 200
        assert resp_key.json()["success"] is True


# ---------------------------------------------------------------------------
# Test 4: Spoofed client-supplied verified_by is ignored/stripped
# ---------------------------------------------------------------------------

def test_4_spoofed_verified_by_is_ignored(client: TestClient, sample_payload):
    """Verify that client-supplied verified_by cannot forge human verification attribution."""
    sample_payload["verified_by"] = "unauthorized-spoofed-sre"
    sample_payload["memory_status"] = "DRAFT"

    headers = {"X-API-Key": "sre-key-oncall"}

    captured_payload = None

    async def fake_retain(p):
        nonlocal captured_payload
        captured_payload = p
        return {"success": True, "status": "retained"}

    with patch.object(hindsight_service, "retain_incident", side_effect=fake_retain):
        response = client.post("/api/memory/retain", json=sample_payload, headers=headers)
        assert response.status_code == 200

        # Invariant: verified_by must be stripped to None
        assert captured_payload is not None
        assert captured_payload.verified_by is None
        assert captured_payload.memory_status == MemoryStatus.DRAFT
        assert captured_payload.source_type == MemorySourceType.AI_DRAFT


# ---------------------------------------------------------------------------
# Test 5: Spoofed client-supplied VERIFIED cannot bypass provenance
# ---------------------------------------------------------------------------

def test_5_spoofed_verified_status_cannot_bypass_provenance(client: TestClient, sample_payload):
    """Verify that an unverified incident claiming VERIFIED status is demoted to DRAFT."""
    sample_payload["memory_status"] = "VERIFIED"
    sample_payload["verified_by"] = "lead-sre-alice"

    headers = {"X-API-Key": "sre-key-oncall"}

    captured_payload = None

    async def fake_retain(p):
        nonlocal captured_payload
        captured_payload = p
        return {"success": True, "status": "retained"}

    with patch.object(hindsight_service, "retain_incident", side_effect=fake_retain):
        response = client.post("/api/memory/retain", json=sample_payload, headers=headers)
        assert response.status_code == 200

        # Invariant: Demoted to DRAFT with verified_by=None because no prior human audit exists
        assert captured_payload is not None
        assert captured_payload.memory_status == MemoryStatus.DRAFT
        assert captured_payload.source_type == MemorySourceType.AI_DRAFT
        assert captured_payload.verified_by is None


# ---------------------------------------------------------------------------
# Test 6: Endpoint is marked as deprecated in OpenAPI documentation
# ---------------------------------------------------------------------------

def test_6_endpoint_is_marked_deprecated():
    """Verify that POST /api/memory/retain is marked as deprecated in the OpenAPI spec."""
    openapi = app.openapi()
    paths = openapi.get("paths", {})
    retain_post = paths.get("/api/memory/retain", {}).get("post")

    assert retain_post is not None, "Route /api/memory/retain must exist in OpenAPI paths"
    assert retain_post.get("deprecated") is True, "Route /api/memory/retain must be marked as deprecated"
