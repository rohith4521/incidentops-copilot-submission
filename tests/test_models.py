"""Tests for domain data models and truthful metrics."""

import pytest
from app.models.alert import AlertPayload, AlertSeverity, AlertSource
from app.models.memory import IncidentMemoryItem, MatchStrength, RecallResultSummary
from app.models.runbook import (
    ApprovalStatus,
    RunbookAction,
    RunbookRecommendation,
)
from app.models.triage import RootCauseAnalysis, TriageResult


def test_match_strength_truthful_metrics():
    """Verify MatchStrength strictly adheres to categorical values: High, Moderate, None.

    No uncalculated numerical percentages allowed (Invariant 3).
    """
    valid_strengths = [m.value for m in MatchStrength]
    assert "High" in valid_strengths
    assert "Moderate" in valid_strengths
    assert "None" in valid_strengths
    assert len(valid_strengths) == 3

    # Attempting to assign numerical string raises ValueError
    with pytest.raises(ValueError):
        MatchStrength("92%")


def test_runbook_default_status_is_pending_approval():
    """Verify RunbookRecommendation strictly defaults to PENDING_APPROVAL (Invariant 4)."""
    rb = RunbookRecommendation(
        runbook_id="RB-TEST",
        title="Test Runbook",
        justification="Verified in past incident",
        blast_radius_analysis="Local pod only",
    )
    assert rb.status == ApprovalStatus.PENDING_APPROVAL
    assert rb.approver is None
    assert rb.approval_timestamp is None


def test_triage_result_structure(sample_known_alert):
    """Verify TriageResult model composition."""
    res = TriageResult(
        alert_id=sample_known_alert.id,
        match_strength=MatchStrength.HIGH,
        novelty_detected=False,
        evidence_bullets=["Matched checkout-service in INC-402"],
        triage_summary="Documented incident precedent found in INC-402.",
        root_cause_analysis=RootCauseAnalysis(
            hypothesis="Connection pool starvation",
            contributing_factors=["Traffic spike", "No reap timeout"],
            blast_radius="checkout-service callers",
            affected_components=["checkout-service"],
        ),
        immediate_mitigation="Trigger failover and rollout restart",
        model_used="test-model",
    )
    assert res.match_strength == MatchStrength.HIGH
    assert not res.novelty_detected
    assert len(res.evidence_bullets) == 1
