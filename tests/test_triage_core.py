"""Focused tests for Phase 2 Triage Core flow.

Tests:
1. Known Hindsight match (INC-104)
2. Novel incident (stateless first-principles, no fabricated history)
3. Stateless mode (enable_memory=false)
4. Hindsight/Groq failure resilience
"""

import os
from unittest.mock import AsyncMock, patch
import pytest
from app.models.memory import MatchStrength, RecallResultSummary
from app.services.hindsight_service import hindsight_service


def test_known_hindsight_match_inc_104(client, inc_104_recall_summary):
    """Scenario 1: Operational alert matching historical incident INC-104 (offline mock boundary)."""
    payload = {
        "service": "payment-api",
        "alert": "PaymentGatewayEgressTimeoutBreached",
        "symptoms": [
            "Outbound HTTPS timeout > 30s calling Stripe payment gateway API",
            "Egress HTTP thread pool saturation across 8 replicas",
            "Cascading HTTP 504 Gateway Timeout on /api/v2/checkout/charge",
        ],
        "severity": "CRITICAL",
        "context": {"cluster": "k8s-prod-us-east-1"},
        "enable_memory": True,
    }

    with patch.object(
        hindsight_service,
        "recall_incident_memory",
        new_callable=AsyncMock,
        return_value=inc_104_recall_summary,
    ):
        response = client.post("/api/triage", json=payload)
        assert response.status_code == 200

        data = response.json()

    # 10 Required Structured Fields
    for field in [
        "incident_summary",
        "likely_root_cause",
        "supporting_evidence",
        "historical_matches",
        "recommended_runbook",
        "failed_mitigations_to_avoid",
        "reasoning_summary",
        "requires_human_approval",
        "memory_used",
        "novelty",
    ]:
        assert field in data, f"Missing required field: {field}"

    assert data["memory_used"] is True
    assert data["novelty"] is False
    assert data["requires_human_approval"] is True

    # Historical matches should link to INC-104
    matches = data["historical_matches"]
    assert len(matches) > 0
    matched_ids = [m["incident_id"] for m in matches]
    assert "INC-104" in matched_ids

    # Historical failed mitigations should be present
    failed_mitigations = data["failed_mitigations_to_avoid"]
    assert len(failed_mitigations) > 0
    assert any("Restarting payment-api pods alone" in fm for fm in failed_mitigations)

    # Verified runbook should be recommended and pending approval
    runbook = data["recommended_runbook"]
    assert runbook is not None
    assert runbook["runbook_id"] == "RB-PAYMENT-CIRCUIT-SHED"
    assert runbook["status"] == "PENDING_APPROVAL"


def test_novel_incident(client):
    """Scenario 2: Novel failure mode with no historical match in Hindsight."""
    payload = {
        "service": "event-stream-consumer",
        "alert": "Kafka Deserialization Trap and Partition Skew",
        "symptoms": [
            "Consumer lag surging past 400k messages on partition 7",
            "Unhandled RecordDeserializationException in consumer logs",
            "No dead-letter queue configured for corrupt Avro magic byte 0x7F",
        ],
        "severity": "CRITICAL",
        "context": {"cluster": "k8s-prod-us-west-2"},
        "enable_memory": True,
    }

    novel_recall = RecallResultSummary(
        match_strength=MatchStrength.NONE,
        is_novel=True,
        memories_found=[],
        candidates_retrieved=[],
        raw_recall_count=0,
        query_used="Service: event-stream-consumer. Alert: Kafka Deserialization Trap and Partition Skew.",
        hindsight_connected=True,
        evidence_bullets=["No historical incidents found in Hindsight memory."],
    )

    with patch.object(
        hindsight_service,
        "recall_incident_memory",
        new_callable=AsyncMock,
        return_value=novel_recall,
    ):
        response = client.post("/api/triage", json=payload)
        assert response.status_code == 200

        data = response.json()

        assert data["memory_used"] is True
        assert data["novelty"] is True
        assert data["requires_human_approval"] is True

        # Invariant: Never fabricate history
        assert data["historical_matches"] == []

        # Required novelty preamble
        assert "No sufficiently relevant historical incident found" in data["incident_summary"]

        # Recommended diagnostic runbook pending approval
        assert data["recommended_runbook"] is not None
        assert data["recommended_runbook"]["status"] == "PENDING_APPROVAL"
        assert len(data["failed_mitigations_to_avoid"]) > 0


def test_stateless_mode(client):
    """Scenario 3: Explicit stateless triage (enable_memory=False)."""
    payload = {
        "service": "payment-api",
        "alert": "PaymentGatewayEgressTimeoutBreached",
        "symptoms": ["Outbound HTTPS timeout > 30s calling Stripe payment gateway API"],
        "severity": "CRITICAL",
        "enable_memory": False,
    }

    response = client.post("/api/triage", json=payload)
    assert response.status_code == 200

    data = response.json()

    # Memory layer must not be used
    assert data["memory_used"] is False
    assert data["novelty"] is True
    assert data["historical_matches"] == []
    assert data["requires_human_approval"] is True
    assert "Stateless" in data["incident_summary"]
    assert data["recommended_runbook"] is not None
    assert data["recommended_runbook"]["status"] == "PENDING_APPROVAL"


def test_hindsight_failure_resilience(client):
    """Scenario 4A: Hindsight service failure falls back gracefully without 500 error."""
    payload = {
        "service": "payment-api",
        "alert": "PaymentGatewayEgressTimeoutBreached",
        "symptoms": ["Outbound HTTPS timeout > 30s"],
        "severity": "HIGH",
        "enable_memory": True,
    }

    with patch.object(
        hindsight_service,
        "recall_incident_memory",
        side_effect=Exception("Hindsight connection timeout"),
    ):
        response = client.post("/api/triage", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["novelty"] is True
        assert data["requires_human_approval"] is True
        assert data["recommended_runbook"] is not None
        assert data["historical_matches"] == []


def test_groq_failure_resilience(client):
    """Scenario 4B: Groq inference failure triggers first-principles fallback cleanly."""
    payload = {
        "service": "order-service",
        "alert": "OrderDeadlockBurst",
        "symptoms": ["Deadlock detected in order repository"],
        "severity": "HIGH",
        "enable_memory": False,
    }

    from app.services.groq_service import groq_service
    with patch.object(
        groq_service,
        "_get_client",
        side_effect=Exception("Groq API quota exhausted"),
    ):
        response = client.post("/api/triage", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["requires_human_approval"] is True
        assert data["recommended_runbook"] is not None
        assert len(data["supporting_evidence"]) > 0


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("HINDSIGHT_LIVE_TEST"),
    reason="Live Hindsight integration test skipped by default. Set HINDSIGHT_LIVE_TEST=1 to execute.",
)
def test_known_hindsight_match_inc_104_live(client):
    """Scenario 1 (Live Integration): Alert matching INC-104 directly against live Hindsight server."""
    payload = {
        "service": "payment-api",
        "alert": "PaymentGatewayEgressTimeoutBreached",
        "symptoms": [
            "Outbound HTTPS timeout > 30s calling Stripe payment gateway API",
            "Egress HTTP thread pool saturation across 8 replicas",
            "Cascading HTTP 504 Gateway Timeout on /api/v2/checkout/charge",
        ],
        "severity": "CRITICAL",
        "context": {"cluster": "k8s-prod-us-east-1"},
        "enable_memory": True,
    }

    response = client.post("/api/triage", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["memory_used"] is True
    assert data["novelty"] is False
    assert any("INC-104" in m["incident_id"] for m in data["historical_matches"])
