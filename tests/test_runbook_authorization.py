"""PHASE 7.4C — Secure Runbook Approval / RBAC Tests.

Validates:
1. Anonymous approve request returns HTTP 401 Unauthorized.
2. Anonymous reject request returns HTTP 401 Unauthorized.
3. AI identity approve request returns HTTP 403 Forbidden.
4. AI identity reject request returns HTTP 403 Forbidden.
5. Authenticated human approve request succeeds and sets status=APPROVED.
6. Authenticated human reject request succeeds and sets status=REJECTED.
7. Client-supplied forged approver field is ignored; authenticated identity is used instead.
8. Client-supplied forged approved_by / rejected_by fields are ignored.
9. Authenticated identity appears in resulting recommendation and simulation audit log.
10. Existing dry-run simulation remains strictly non-destructive.
"""

from unittest.mock import patch
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.models.runbook import (
    ApprovalStatus,
    RunbookAction,
    RunbookRecommendation,
)
from app.services.auth_service import create_access_token
from app.services.runbook_service import runbook_service


@pytest.fixture
def client():
    """FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture
def registered_recommendation():
    """Register a fresh RunbookRecommendation in PENDING_APPROVAL state."""
    rec = RunbookRecommendation(
        runbook_id="RB-TEST-DATABASE-FAILOVER",
        title="PostgreSQL Standby Promotion Runbook",
        justification="INC-108 database failover mitigation precedent",
        blast_radius_analysis="Read-only query degradation for ~45 seconds during election",
        actions=[
            RunbookAction(
                step_number=1,
                name="Promote Replica",
                command="pg_ctl promote -D /var/lib/postgresql/data",
                target_component="postgres-replica-01",
                description="Promote warm standby to primary",
            ),
            RunbookAction(
                step_number=2,
                name="Update DNS",
                command="consul kv put services/db/master pg-02.internal",
                target_component="service-discovery",
                description="Update primary database endpoint in consul",
            ),
        ],
    )
    runbook_service.register_recommendation(rec)
    return rec


# ---------------------------------------------------------------------------
# Test 1 & 2: Anonymous Approve & Reject Return 401
# ---------------------------------------------------------------------------

def test_1_anonymous_approve_returns_401(client: TestClient, registered_recommendation):
    """Verify that unauthenticated approve requests are rejected with HTTP 401."""
    resp = client.post(
        f"/api/runbooks/{registered_recommendation.id}/approve",
        json={"notes": "Attempting anonymous approval"},
    )
    assert resp.status_code == 401
    assert "Authentication credentials required" in resp.json()["detail"]


def test_2_anonymous_reject_returns_401(client: TestClient, registered_recommendation):
    """Verify that unauthenticated reject requests are rejected with HTTP 401."""
    resp = client.post(
        f"/api/runbooks/{registered_recommendation.id}/reject",
        json={"reason": "Attempting anonymous rejection"},
    )
    assert resp.status_code == 401
    assert "Authentication credentials required" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Test 3 & 4: AI Identity Approve & Reject Return 403
# ---------------------------------------------------------------------------

def test_3_ai_identity_approve_returns_403(client: TestClient, registered_recommendation):
    """Verify that AI agents attempting to approve a runbook are rejected with HTTP 403."""
    ai_token = create_access_token(identity="copilot-triage-ai", role="ai_agent", is_human=False)
    headers = {"Authorization": f"Bearer {ai_token}"}

    resp = client.post(
        f"/api/runbooks/{registered_recommendation.id}/approve",
        json={"notes": "AI attempting self-approval"},
        headers=headers,
    )
    assert resp.status_code == 403
    assert "AI agents are strictly forbidden" in resp.json()["detail"]


def test_4_ai_identity_reject_returns_403(client: TestClient, registered_recommendation):
    """Verify that AI agents attempting to reject a runbook are rejected with HTTP 403."""
    ai_token = create_access_token(identity="copilot-triage-ai", role="ai_agent", is_human=False)
    headers = {"Authorization": f"Bearer {ai_token}"}

    resp = client.post(
        f"/api/runbooks/{registered_recommendation.id}/reject",
        json={"reason": "AI attempting rejection"},
        headers=headers,
    )
    assert resp.status_code == 403
    assert "AI agents are strictly forbidden" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Test 5 & 6: Authenticated Human SRE Approve & Reject Succeed
# ---------------------------------------------------------------------------

def test_5_authenticated_human_approve_allowed(client: TestClient, registered_recommendation):
    """Verify that authenticated human SRE can approve a runbook."""
    human_token = create_access_token(identity="lead-sre-alice", role="sre", is_human=True)
    headers = {"Authorization": f"Bearer {human_token}"}

    resp = client.post(
        f"/api/runbooks/{registered_recommendation.id}/approve",
        json={"notes": "Approved for emergency mitigation during incident triage"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "APPROVED"
    assert data["approver"] == "lead-sre-alice"
    assert data["approval_timestamp"] is not None


def test_6_authenticated_human_reject_allowed(client: TestClient, registered_recommendation):
    """Verify that authenticated human SRE can reject a runbook with an operational reason."""
    human_token = create_access_token(identity="lead-sre-bob", role="sre", is_human=True)
    headers = {"Authorization": f"Bearer {human_token}"}

    resp = client.post(
        f"/api/runbooks/{registered_recommendation.id}/reject",
        json={"reason": "Mitigation blast radius too broad for current traffic window"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "REJECTED"
    assert data["approver"] == "lead-sre-bob"
    assert data["rejection_reason"] == "Mitigation blast radius too broad for current traffic window"


# ---------------------------------------------------------------------------
# Test 7 & 8: Forged Client Approver / Rejector Fields Are Ignored
# ---------------------------------------------------------------------------

def test_7_forged_approver_field_is_ignored(client: TestClient, registered_recommendation):
    """Verify that client-supplied approver, approved_by, or verifier fields are ignored."""
    headers = {"X-API-Key": "sre-key-oncall"}  # Identity in mapping: "oncall-sre"

    # Client attempts to spoof approver as CTO or another engineer
    forged_body = {
        "approver": "spoofed-cto-executive",
        "approved_by": "spoofed-vp-engineering",
        "verifier": "spoofed-auditor",
        "notes": "Emergency signoff",
    }

    resp = client.post(
        f"/api/runbooks/{registered_recommendation.id}/approve",
        json=forged_body,
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # Invariant: approver MUST be the authenticated identity ("oncall-sre"), NOT spoofed
    assert data["approver"] == "oncall-sre"
    assert data["approver"] != "spoofed-cto-executive"


def test_8_forged_rejected_by_field_is_ignored(client: TestClient, registered_recommendation):
    """Verify that client-supplied rejector / approver fields in rejection are ignored."""
    headers = {"X-API-Key": "sre-key-oncall"}  # Identity in mapping: "oncall-sre"

    forged_body = {
        "approver": "spoofed-team-lead",
        "rejected_by": "spoofed-team-lead",
        "verifier": "spoofed-team-lead",
        "reason": "Replica lag too high",
    }

    resp = client.post(
        f"/api/runbooks/{registered_recommendation.id}/reject",
        json=forged_body,
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["approver"] == "oncall-sre"
    assert data["approver"] != "spoofed-team-lead"


# ---------------------------------------------------------------------------
# Test 9 & 10: Authenticated Identity in Audit Log & Non-Destructive Dry Run
# ---------------------------------------------------------------------------

def test_9_authenticated_identity_in_simulation_audit(client: TestClient, registered_recommendation):
    """Verify that the authenticated approver identity is bound into the simulation audit log."""
    human_token = create_access_token(identity="senior-sre-charlie", role="sre", is_human=True)
    headers = {"Authorization": f"Bearer {human_token}"}

    # Step 1: Approve with authenticated token
    approve_resp = client.post(
        f"/api/runbooks/{registered_recommendation.id}/approve",
        json={"notes": "Pre-approved for load shift testing"},
        headers=headers,
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["approver"] == "senior-sre-charlie"

    # Step 2: Simulate runbook
    sim_resp = client.post(
        f"/api/runbooks/{registered_recommendation.id}/simulate",
        json={"executor": "operator-dan"},
    )
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()
    assert sim_data["success"] is True

    # Audit logs must contain the authenticated approver identity
    logs_str = " ".join(sim_data["logs"])
    assert "senior-sre-charlie" in logs_str
    assert "[AUTHORIZATION] Validated human approval by 'senior-sre-charlie'" in logs_str


def test_10_dry_run_simulation_remains_strictly_non_destructive(client: TestClient, registered_recommendation):
    """Verify that simulation is purely dry-run and non-destructive."""
    human_token = create_access_token(identity="lead-sre-alice", role="sre", is_human=True)
    headers = {"Authorization": f"Bearer {human_token}"}

    client.post(
        f"/api/runbooks/{registered_recommendation.id}/approve",
        json={"notes": "Approved for non-destructive dry-run"},
        headers=headers,
    )

    sim_resp = client.post(
        f"/api/runbooks/{registered_recommendation.id}/simulate",
        json={"executor": "lead-sre-alice"},
    )
    assert sim_resp.status_code == 200
    data = sim_resp.json()
    assert data["success"] is True
    # Verify simulation flags and mock output
    assert any("[DRY-RUN OK]" in log for log in data["logs"])
    assert "DRY-RUN EXECUTION STEPS" in " ".join(data["logs"])
    assert data["projected_recovery_time_minutes"] > 0
