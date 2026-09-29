"""Tests for Human-in-the-Loop runbook approval and simulation enforcement (Invariant 4)."""

import pytest
from app.models.runbook import (
    ApprovalStatus,
    RunbookAction,
    RunbookRecommendation,
)
from app.services.runbook_service import (
    RunbookApprovalError,
    RunbookService,
)


def test_simulation_blocked_without_human_approval():
    """Verify that simulating an unapproved runbook raises RunbookApprovalError."""
    service = RunbookService()
    rec = RunbookRecommendation(
        runbook_id="RB-TEST-FAILOVER",
        title="Test Redis Sentinel Failover",
        justification="INC-402 precedent",
        blast_radius_analysis="Minor latency bump",
        actions=[
            RunbookAction(
                step_number=1,
                name="Check Master",
                command="redis-cli info",
                target_component="redis",
                description="Check status",
            )
        ],
    )
    service.register_recommendation(rec)

    # Invariant 4 gate check: Must raise error when status is PENDING_APPROVAL
    with pytest.raises(RunbookApprovalError) as exc_info:
        service.simulate_runbook(rec.id, executor="devops-eng")

    assert "requires human approval before simulation" in str(exc_info.value)
    assert "PENDING_APPROVAL" in str(exc_info.value)


def test_simulation_succeeds_after_human_approval():
    """Verify that simulating an approved runbook succeeds and records audit trail."""
    service = RunbookService()
    rec = RunbookRecommendation(
        runbook_id="RB-TEST-EXPAND",
        title="Expand Memory Limit",
        justification="INC-519 precedent",
        blast_radius_analysis="Zero downtime rolling update",
        actions=[
            RunbookAction(
                step_number=1,
                name="Patch memory limit",
                command="kubectl set resources ...",
                target_component="auth-api",
                description="Increase heap headroom",
            )
        ],
    )
    service.register_recommendation(rec)

    # Approve runbook
    approved_rec = service.approve_runbook(
        recommendation_id=rec.id,
        approver="alice@sre-team.internal",
        notes="Validated against production budget",
    )
    assert approved_rec.status == ApprovalStatus.APPROVED
    assert approved_rec.approver == "alice@sre-team.internal"
    assert approved_rec.approval_timestamp is not None

    # Now simulate should succeed
    sim_result = service.simulate_runbook(rec.id, executor="alice@sre-team.internal")
    assert sim_result.success is True
    assert sim_result.executed_by == "alice@sre-team.internal"
    assert any("[AUDIT]" in line for line in sim_result.logs)
    assert any("alice@sre-team.internal" in line for line in sim_result.logs)
