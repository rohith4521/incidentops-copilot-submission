"""Focused tests for Phase 6.2A Hindsight Failure Handling.

Covers:
1. Hindsight success (normal healthy memory recall).
2. Connection failure (network/connectivity drop handled gracefully without 500).
3. Timeout failure (request timeout handled gracefully without 500).
4. Triage still succeeds without memory (complete 10-invariant first-principles triage report).
5. No false historical evidence (zero fabricated matches, zero fake runbook IDs, match_strength='None').
"""

import asyncio
from unittest.mock import AsyncMock, patch
import pytest

from app.models.memory import MatchStrength, IncidentMemoryItem, RecallResultSummary
from app.services.hindsight_service import hindsight_service


@pytest.fixture
def payment_alert_payload():
    return {
        "service": "payment-api",
        "alert": "PaymentGatewayEgressTimeoutBreached",
        "symptoms": [
            "Outbound HTTPS timeout > 30s calling Stripe payment gateway API",
            "Egress HTTP thread pool saturation across 8 replicas",
        ],
        "severity": "CRITICAL",
        "context": {"cluster": "k8s-prod-us-east-1"},
        "enable_memory": True,
    }


# ---------------------------------------------------------------------------
# Test 1: Hindsight Success
# ---------------------------------------------------------------------------

def test_hindsight_success(client, payment_alert_payload):
    """Verify healthy Hindsight recall provides verified memory and positive memory flags."""
    verified_item = IncidentMemoryItem(
        id="mem-104",
        incident_id="INC-104",
        service="payment-api",
        title="Stripe Egress Connection Exhaustion",
        root_cause="Stripe API gateway latency spike caused connection pool exhaustion.",
        verified_runbook="RB-PAYMENT-EGRESS-TIMEOUT",
        runbook_used="RB-PAYMENT-EGRESS-TIMEOUT",
        failed_mitigations=["Rolling restart of payment pods aggravated connection storm."],
        postmortem_summary="Resolved by tripping circuit breaker and increasing socket connect timeout.",
        memory_status="VERIFIED",
        source_type="HUMAN_VERIFIED",
    )
    healthy_recall = RecallResultSummary(
        match_strength=MatchStrength.HIGH,
        is_novel=False,
        memories_found=[verified_item],
        evidence_bullets=["Matched verified historical incident INC-104"],
        query_used="PaymentGatewayEgressTimeoutBreached",
        hindsight_connected=True,
    )

    with patch.object(
        hindsight_service,
        "recall_incident_memory",
        new_callable=AsyncMock,
        return_value=healthy_recall,
    ):
        response = client.post("/api/triage", json=payment_alert_payload)
        assert response.status_code == 200

        data = response.json()
        assert data["memory_available"] is True
        assert data["memory_used"] is True
        assert data["degradation_reason"] is None
        assert data["novelty"] is False
        assert len(data["historical_matches"]) == 1
        assert data["historical_matches"][0]["incident_id"] == "INC-104"
        assert data["recommended_runbook"]["historical_reference_id"] == "INC-104"


# ---------------------------------------------------------------------------
# Test 2: Connection Failure
# ---------------------------------------------------------------------------

def test_hindsight_connection_failure(client, payment_alert_payload):
    """Verify Hindsight connection failure does not cause 500 and exposes degradation flags."""
    with patch.object(
        hindsight_service,
        "recall_incident_memory",
        side_effect=ConnectionRefusedError("Failed to establish connection to Hindsight API:8888"),
    ):
        response = client.post("/api/triage", json=payment_alert_payload)
        assert response.status_code == 200

        data = response.json()
        assert data["memory_available"] is False
        assert data["memory_used"] is False
        assert data["degradation_reason"] == "hindsight_unavailable"
        assert data["novelty"] is True
        assert data["historical_matches"] == []
        assert data["recommended_runbook"] is not None
        assert data["recommended_runbook"]["historical_reference_id"] is None


# ---------------------------------------------------------------------------
# Test 3: Request Timeout
# ---------------------------------------------------------------------------

def test_hindsight_timeout(client, payment_alert_payload):
    """Verify Hindsight request timeout does not cause 500 and degrades gracefully."""
    with patch.object(
        hindsight_service,
        "recall_incident_memory",
        side_effect=asyncio.TimeoutError("Hindsight API call exceeded 10.0s timeout"),
    ):
        response = client.post("/api/triage", json=payment_alert_payload)
        assert response.status_code == 200

        data = response.json()
        assert data["memory_available"] is False
        assert data["memory_used"] is False
        assert data["degradation_reason"] == "hindsight_unavailable"
        assert data["novelty"] is True
        assert data["historical_matches"] == []
        assert data["recommended_runbook"] is not None
        assert data["recommended_runbook"]["historical_reference_id"] is None


# ---------------------------------------------------------------------------
# Test 4: Triage Still Succeeds Without Memory
# ---------------------------------------------------------------------------

def test_triage_still_succeeds_without_memory(client, payment_alert_payload):
    """Verify that triage returns a complete 10-invariant SRE report when Hindsight is dead."""
    with patch.object(
        hindsight_service,
        "recall_incident_memory",
        side_effect=RuntimeError("Hindsight cluster unreachable: 502 Bad Gateway"),
    ):
        response = client.post("/api/triage", json=payment_alert_payload)
        assert response.status_code == 200

        data = response.json()

        # All 10 invariant fields must be present and valid
        required_fields = [
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
        ]
        for f in required_fields:
            assert f in data, f"Missing required invariant field: {f}"

        assert data["memory_used"] is False
        assert data["memory_available"] is False
        assert data["degradation_reason"] == "hindsight_unavailable"
        assert data["requires_human_approval"] is True
        assert data["recommended_runbook"]["status"] == "PENDING_APPROVAL"
        assert len(data["recommended_runbook"]["actions"]) > 0


# ---------------------------------------------------------------------------
# Test 5: No False Historical Evidence
# ---------------------------------------------------------------------------

def test_no_false_historical_evidence_when_hindsight_fails(client, payment_alert_payload):
    """Verify zero fabricated historical matches, runbooks, or confidence when Hindsight fails."""
    with patch.object(
        hindsight_service,
        "recall_incident_memory",
        side_effect=Exception("Fatal Hindsight memory bank corruption"),
    ):
        response = client.post("/api/triage", json=payment_alert_payload)
        assert response.status_code == 200

        data = response.json()

        # Strict evidence truthfulness invariants
        assert data["historical_matches"] == [], "Historical matches must be empty when memory fails"
        assert data["candidates_recalled"] == [], "Candidates must be empty when memory fails"
        assert data["match_strength"] == "None", "Match strength must be 'None'"
        assert data["novelty"] is True, "Incident must be marked novel"
        assert data["recommended_runbook"]["historical_reference_id"] is None
        assert data["incident_summary"].startswith("No sufficiently relevant historical incident found")

        # Factual evidence must not claim historical matches
        for bullet in data["supporting_evidence"]:
            assert "Matched verified historical incident" not in bullet
            assert "INC-104" not in bullet
