"""Tests for SRE triage engine and novelty handling (Invariant 5)."""

import pytest
from app.models.memory import MatchStrength, RecallResultSummary
from app.services.groq_service import GroqInferenceService
from app.services.triage_engine import TriageOrchestrationEngine


@pytest.mark.asyncio
async def test_novelty_handling_enforces_required_prefix(sample_novel_alert):
    """Verify Invariant 5: If alert is novel, triage_summary MUST start with

    'No sufficiently relevant historical incident found.'
    """
    engine = TriageOrchestrationEngine()
    result = await engine.execute_triage(sample_novel_alert)

    assert result.match_strength == MatchStrength.NONE
    assert result.novelty_detected is True
    assert result.triage_summary.startswith("No sufficiently relevant historical incident found")


@pytest.mark.asyncio
async def test_triage_registers_recommended_runbook(sample_known_alert):
    """Verify that triage automatically registers the recommended runbook with PENDING_APPROVAL status."""
    engine = TriageOrchestrationEngine()
    result = await engine.execute_triage(sample_known_alert)

    assert result.recommended_runbook is not None
    rb = result.recommended_runbook
    assert rb.status.value == "PENDING_APPROVAL"

    # Verify registered in runbook service
    registered = engine.runbooks.get_recommendation(rb.id)
    assert registered is not None
    assert registered.id == rb.id
