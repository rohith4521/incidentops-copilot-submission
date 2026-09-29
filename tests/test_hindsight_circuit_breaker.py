"""Focused tests for Phase 7.6 Hindsight Circuit Breaker.

Covers:
1. CLOSED normal recall.
2. Threshold failure opens circuit.
3. OPEN fails fast without Hindsight call.
4. Stateless degradation contains no historical evidence.
5. Valid empty recall does not open circuit.
6. HALF_OPEN recovery.
7. HALF_OPEN failure reopens circuit.
8. Concurrent requests do not create multiple recovery probes.
9. Circuit state is observable through health/metrics.
"""

import asyncio
from unittest.mock import AsyncMock, patch
import pytest

from app.models.alert import AlertPayload, AlertSeverity
from app.models.memory import IncidentMemoryItem, MatchStrength, RecallResultSummary
from app.services.circuit_breaker import CircuitOpenError, CircuitState, HindsightCircuitBreaker
from app.services.hindsight_service import hindsight_service


@pytest.fixture(autouse=True)
def reset_circuit_breaker():
    """Ensure circuit breaker starts in pristine state before and after each test."""
    hindsight_service.circuit_breaker.reset()
    yield
    hindsight_service.circuit_breaker.reset()


@pytest.fixture
def sample_alert_payload():
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
# Test 1: CLOSED normal recall
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_1_closed_normal_recall():
    """Verify normal recall in CLOSED state succeeds and resets failure counts."""
    cb = hindsight_service.circuit_breaker
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0

    alert = AlertPayload(
        service="payment-api",
        title="PaymentGatewayEgressTimeoutBreached",
        description="Outbound HTTPS timeouts calling payment processor",
        symptoms=["Outbound HTTPS timeout > 30s"],
        severity=AlertSeverity.HIGH,
    )

    allowed, reason = await cb.can_execute()
    assert allowed is True
    assert reason is None

    # Simulate success
    await cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


# ---------------------------------------------------------------------------
# Test 2: Threshold failure opens circuit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_2_threshold_failure_opens_circuit():
    """Verify consecutive dependency failures reach threshold and trip CLOSED -> OPEN."""
    cb = HindsightCircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
    assert cb.state == CircuitState.CLOSED

    # Failure 1
    tripped = await cb.record_failure(ConnectionRefusedError("Connection refused: 8888"))
    assert tripped is False
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 1

    # Failure 2
    tripped = await cb.record_failure(asyncio.TimeoutError("Timeout breached"))
    assert tripped is False
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 2

    # Failure 3 (Threshold reached)
    tripped = await cb.record_failure(ConnectionResetError("Connection reset by peer"))
    assert tripped is True
    assert cb.state == CircuitState.OPEN
    assert cb.is_open is True
    assert cb.failure_count == 3


# ---------------------------------------------------------------------------
# Test 3: OPEN fails fast without Hindsight call
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_3_open_fails_fast_without_hindsight_call():
    """Verify that when OPEN, recall returns immediately without invoking Hindsight client."""
    cb = hindsight_service.circuit_breaker
    cb.failure_threshold = 2
    # Force trip to OPEN
    await cb.record_failure(ConnectionRefusedError("Connection refused: 8888"))
    await cb.record_failure(ConnectionRefusedError("Connection refused: 8888"))
    assert cb.state == CircuitState.OPEN

    alert = AlertPayload(
        service="payment-api",
        title="PaymentGatewayEgressTimeoutBreached",
        description="Outbound HTTPS timeouts calling payment processor",
        symptoms=["Outbound HTTPS timeout > 30s"],
        severity=AlertSeverity.HIGH,
    )

    with patch.object(hindsight_service, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client

        summary = await hindsight_service.recall_incident_memory(alert)

        # Assert no call was made to client.arecall
        mock_client.arecall.assert_not_called()
        assert summary.hindsight_connected is False
        assert summary.diagnostic_note == "hindsight_circuit_open"
        assert summary.match_strength == MatchStrength.NONE
        assert summary.memories_found == []
        assert summary.is_novel is True


# ---------------------------------------------------------------------------
# Test 4: Stateless degradation contains no historical evidence
# ---------------------------------------------------------------------------

def test_4_stateless_degradation_contains_no_historical_evidence(client, sample_alert_payload):
    """Verify that triage under OPEN circuit breaker continues statelessly without fake memory."""
    cb = hindsight_service.circuit_breaker
    cb._state = CircuitState.OPEN
    cb._last_failure_time = 9999999999.0  # Far in the future so it stays OPEN

    response = client.post("/api/v1/triage", json=sample_alert_payload)
    assert response.status_code == 200

    data = response.json()
    assert data["memory_used"] is False
    assert data["memory_available"] is False
    assert data["historical_matches"] == []
    assert data["candidates_recalled"] == []
    assert data["degradation_reason"] == "hindsight_circuit_open"
    assert data["novelty"] is True

    # Check evidence doesn't hallucinate historical incidents
    for bullet in data["supporting_evidence"]:
        assert "INC-104" not in bullet
        assert "Matched verified historical incident" not in bullet

    assert data["recommended_runbook"] is not None
    assert data["recommended_runbook"]["historical_reference_id"] is None


# ---------------------------------------------------------------------------
# Test 5: Valid empty recall does not open circuit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_5_valid_empty_recall_does_not_open_circuit():
    """Verify valid empty or no-match recall results count as success, NOT failures."""
    cb = hindsight_service.circuit_breaker
    assert cb.state == CircuitState.CLOSED

    # Non-dependency exceptions (e.g. 404 bank not found or value error) do not trip breaker
    res = await cb.record_failure(ValueError("Invalid alert signature format"))
    assert res is False
    assert cb.failure_count == 0
    assert cb.state == CircuitState.CLOSED

    # Multiple successful empty recalls
    for _ in range(5):
        allowed, _ = await cb.can_execute()
        assert allowed is True
        await cb.record_success()

    assert cb.failure_count == 0
    assert cb.state == CircuitState.CLOSED


# ---------------------------------------------------------------------------
# Test 6: HALF_OPEN recovery
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_6_half_open_recovery():
    """Verify that after recovery timeout, one probe transitions to HALF_OPEN and closes on success."""
    cb = HindsightCircuitBreaker(failure_threshold=2, recovery_timeout=0.05)
    # Trip to OPEN
    await cb.record_failure(ConnectionRefusedError("down"))
    await cb.record_failure(ConnectionRefusedError("down"))
    assert cb.state == CircuitState.OPEN

    # Wait for recovery timeout
    await asyncio.sleep(0.06)

    # Next call acquires probe -> HALF_OPEN
    allowed, reason = await cb.can_execute()
    assert allowed is True
    assert reason is None
    assert cb.state == CircuitState.HALF_OPEN
    assert cb.is_half_open is True

    # Probe succeeds
    await cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.is_closed is True
    assert cb.failure_count == 0


# ---------------------------------------------------------------------------
# Test 7: HALF_OPEN failure reopens circuit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_7_half_open_failure_reopens_circuit():
    """Verify that if the HALF_OPEN probe fails, circuit transitions immediately back to OPEN."""
    cb = HindsightCircuitBreaker(failure_threshold=2, recovery_timeout=0.05)
    await cb.record_failure(ConnectionRefusedError("down"))
    await cb.record_failure(ConnectionRefusedError("down"))
    assert cb.state == CircuitState.OPEN

    await asyncio.sleep(0.06)

    # Acquire probe
    allowed, _ = await cb.can_execute()
    assert allowed is True
    assert cb.state == CircuitState.HALF_OPEN

    # Probe fails
    tripped = await cb.record_failure(asyncio.TimeoutError("probe timed out"))
    assert tripped is True
    assert cb.state == CircuitState.OPEN
    assert cb.is_open is True


# ---------------------------------------------------------------------------
# Test 8: Concurrent requests do not create multiple recovery probes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_8_concurrent_requests_do_not_create_multiple_recovery_probes():
    """Verify that when recovery timeout elapses, exactly 1 request probes; concurrent requests fail fast."""
    cb = HindsightCircuitBreaker(failure_threshold=2, recovery_timeout=0.05)
    await cb.record_failure(ConnectionRefusedError("down"))
    await cb.record_failure(ConnectionRefusedError("down"))
    assert cb.state == CircuitState.OPEN

    await asyncio.sleep(0.06)

    # Fire 10 concurrent requests to can_execute()
    results = await asyncio.gather(*(cb.can_execute() for _ in range(10)))

    allowed_count = sum(1 for allowed, _ in results if allowed is True)
    rejected_count = sum(1 for allowed, _ in results if allowed is False)

    # Exactly one probe allowed!
    assert allowed_count == 1, f"Expected exactly 1 probe, got {allowed_count}"
    assert rejected_count == 9, f"Expected 9 fast fails, got {rejected_count}"
    assert cb.state == CircuitState.HALF_OPEN
    assert cb.get_status()["metrics"]["probe_count"] == 1


# ---------------------------------------------------------------------------
# Test 9: Circuit state is observable through health and metrics
# ---------------------------------------------------------------------------

def test_9_circuit_state_observable_through_health_and_metrics(client):
    """Verify that circuit breaker state is visible in both GET /api/v1/health and GET /api/v1/metrics."""
    cb = hindsight_service.circuit_breaker
    cb.reset()

    # 1. Healthy state
    health_resp = client.get("/api/v1/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert "circuit_breaker" in health_data["dependencies"]["hindsight"]
    assert health_data["dependencies"]["hindsight"]["circuit_breaker"]["state"] == "CLOSED"

    metrics_resp = client.get("/api/v1/metrics")
    assert metrics_resp.status_code == 200
    metrics_data = metrics_resp.json()
    assert "hindsight_circuit_breaker" in metrics_data
    assert metrics_data["hindsight_circuit_breaker"]["state"] == "CLOSED"

    # 2. Trip to OPEN
    cb._state = CircuitState.OPEN
    cb._last_failure_time = 9999999999.0

    health_resp_open = client.get("/api/v1/health")
    assert health_resp_open.status_code == 200
    health_data_open = health_resp_open.json()
    assert health_data_open["dependencies"]["hindsight"]["circuit_breaker"]["state"] == "OPEN"
    assert health_data_open["dependencies"]["hindsight"]["status"] == "circuit_open"
    assert health_data_open["status"] == "degraded"

    metrics_resp_open = client.get("/api/v1/metrics")
    assert metrics_resp_open.status_code == 200
    metrics_data_open = metrics_resp_open.json()
    assert metrics_data_open["hindsight_circuit_breaker"]["state"] == "OPEN"
