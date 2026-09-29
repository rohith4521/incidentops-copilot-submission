"""Focused tests for Phase 6.1 LLM Reliability Hardening.

Covers:
1. Valid response validation (Pydantic schema conformance).
2. Malformed JSON handling (JSONDecodeError -> bounded retry -> degraded fallback).
3. Schema-invalid response handling (Pydantic ValidationError -> bounded retry -> degraded fallback).
4. Request timeout handling (LLMTimeoutError -> bounded retry -> degraded fallback).
5. Bounded retry success with exponential backoff (transient failure recovered).
6. Primary provider failure + fallback provider success (failover chain).
7. All providers unavailable returns valid 200 DEGRADED response (no unhandled 500).
8. Degraded memory-evidence-only response uses only trusted Hindsight evidence without fabrication.
"""

import asyncio
import json
from unittest.mock import AsyncMock, patch
import pytest

from app.config import settings
from app.models.memory import MatchStrength, IncidentMemoryItem, RecallResultSummary
from app.models.triage import TriageRequest
from app.services.groq_service import groq_service
from app.services.hindsight_service import hindsight_service
from app.services.llm_provider import (
    BaseLLMProvider,
    FallbackProvider,
    LLMProviderRegistry,
)


# ---------------------------------------------------------------------------
# Test Helpers & Mock Providers
# ---------------------------------------------------------------------------

VALID_LLM_JSON = json.dumps({
    "incident_summary": "Degradation caused by thread pool exhaustion in upstream connection pool.",
    "likely_root_cause": "Outbound socket connection pool saturated under peak egress load.",
    "supporting_evidence": [
        "Thread pool saturation observed across all 8 pods",
        "Egress timeout > 30s calling downstream gateway",
    ],
    "failed_mitigations_to_avoid": [
        "Avoid rolling restart without shedding ingress client traffic."
    ],
    "recommended_runbook": {
        "runbook_id": "RB-PAYMENT-EGRESS-TIMEOUT",
        "title": "Payment Gateway Timeout Remediation",
        "justification": "Verified mitigation targeting connection pool settings.",
        "historical_reference_id": "INC-104",
        "actions": [
            {
                "step_number": 1,
                "name": "Trip Circuit Breaker",
                "command": "# Trip circuit breaker to isolate payment-api",
                "target_component": "payment-api",
                "is_safe_simulation": True,
                "description": "Isolate degraded connection and queue requests.",
            }
        ],
    },
    "reasoning_summary": "SRE reasoning synthesized based on alert telemetry and precedents.",
})


class MockLLMProvider(BaseLLMProvider):
    """Controllable LLM Provider for unit testing reliability and resilience."""

    def __init__(
        self,
        name: str = "mock_primary",
        responses: list = None,
        exceptions: list = None,
        delays: list = None,
        available: bool = True,
    ):
        self.name = name
        self._responses = list(responses or [])
        self._exceptions = list(exceptions or [])
        self._delays = list(delays or [])
        self._available = available
        self.call_count = 0

    @property
    def is_available(self) -> bool:
        return self._available

    async def generate_triage_json(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = None,
        timeout: float = None,
    ) -> str:
        self.call_count += 1

        if self._delays:
            d = self._delays.pop(0)
            if d > 0:
                await asyncio.sleep(d)

        if self._exceptions:
            exc = self._exceptions.pop(0)
            if exc is not None:
                raise exc

        if self._responses:
            return self._responses.pop(0)

        return VALID_LLM_JSON


@pytest.fixture
def sample_triage_request():
    return TriageRequest(
        service="payment-api",
        alert_title="PaymentGatewayEgressTimeoutBreached",
        severity="CRITICAL",
        normalized_symptoms=[
            "Outbound HTTPS timeout > 30s calling Stripe payment gateway API",
            "Egress HTTP thread pool saturation across 8 replicas",
        ],
        context={"cluster": "k8s-prod-us-east-1"},
        enable_memory=True,
    )


# ---------------------------------------------------------------------------
# Test 1: Valid LLM Response (Pydantic Schema Validation)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_valid_llm_response_schema_validation(sample_triage_request):
    """Verify that a valid JSON response is successfully parsed and validated."""
    mock_provider = MockLLMProvider(name="mock_valid", responses=[VALID_LLM_JSON])

    test_registry = LLMProviderRegistry()
    test_registry.register(mock_provider)

    with patch.object(groq_service, "registry", test_registry):
        response = await groq_service.triage_core(
            request=sample_triage_request,
            recall_summary=None,
            enable_memory=False,
        )

        assert response.is_degraded is False
        assert response.degraded_reason is None
        assert response.llm_provider == "mock_valid"
        assert response.likely_root_cause == "Outbound socket connection pool saturated under peak egress load."
        assert response.recommended_runbook is not None
        assert response.recommended_runbook.runbook_id == "RB-PAYMENT-EGRESS-TIMEOUT"
        assert len(response.recommended_runbook.actions) == 1
        assert response.requires_human_approval is True
        assert mock_provider.call_count == 1


# ---------------------------------------------------------------------------
# Test 2: Malformed JSON Triggers Retry and Falls Back to Degraded Mode
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_malformed_json_triggers_retry_and_degraded_fallback(sample_triage_request):
    """Verify that malformed JSON is retried and triggers graceful degraded triage."""
    malformed_text = "```json\n{ incident_summary: broken unclosed string..."
    mock_provider = MockLLMProvider(
        name="mock_malformed",
        responses=[malformed_text, malformed_text, malformed_text],
    )

    test_registry = LLMProviderRegistry()
    test_registry.register(mock_provider)

    with patch.object(groq_service, "registry", test_registry), \
         patch.object(settings, "llm_max_retries", 2), \
         patch.object(settings, "llm_retry_initial_delay_seconds", 0.01):

        response = await groq_service.triage_core(
            request=sample_triage_request,
            recall_summary=None,
            enable_memory=False,
        )

        # 1 initial attempt + 2 retries = 3 attempts
        assert mock_provider.call_count == 3
        assert response.is_degraded is True
        assert response.llm_provider == "degraded_memory_only"
        assert "LLM providers unavailable" in (response.degraded_reason or "")
        # Response has valid invariant structure, no malformed data reaches output
        assert response.likely_root_cause is not None
        assert response.recommended_runbook is not None


# ---------------------------------------------------------------------------
# Test 3: Schema-Invalid Response Triggers Degraded Fallback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_schema_invalid_response_triggers_degraded_fallback(sample_triage_request):
    """Verify that a response missing mandatory fields is rejected by Pydantic."""
    # Missing 'likely_root_cause' and 'recommended_runbook'
    invalid_schema_json = json.dumps({
        "incident_summary": "Only summary provided",
        "random_field": 42,
    })
    mock_provider = MockLLMProvider(
        name="mock_schema_invalid",
        responses=[invalid_schema_json, invalid_schema_json, invalid_schema_json],
    )

    test_registry = LLMProviderRegistry()
    test_registry.register(mock_provider)

    with patch.object(groq_service, "registry", test_registry), \
         patch.object(settings, "llm_max_retries", 2), \
         patch.object(settings, "llm_retry_initial_delay_seconds", 0.01):

        response = await groq_service.triage_core(
            request=sample_triage_request,
            recall_summary=None,
            enable_memory=False,
        )

        assert mock_provider.call_count == 3
        assert response.is_degraded is True
        assert response.llm_provider == "degraded_memory_only"
        assert "LLM providers unavailable" in (response.degraded_reason or "")


# ---------------------------------------------------------------------------
# Test 4: Request Timeout Triggers Degraded Fallback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_timeout_triggers_retry_and_degraded_fallback(sample_triage_request):
    """Verify that requests exceeding llm_timeout_seconds are aborted and retried."""
    # Delay longer than the configured timeout
    mock_provider = MockLLMProvider(
        name="mock_timeout",
        delays=[0.05, 0.05, 0.05],
    )

    test_registry = LLMProviderRegistry()
    test_registry.register(mock_provider)

    with patch.object(groq_service, "registry", test_registry), \
         patch.object(settings, "llm_timeout_seconds", 0.01), \
         patch.object(settings, "llm_max_retries", 1), \
         patch.object(settings, "llm_retry_initial_delay_seconds", 0.005):

        response = await groq_service.triage_core(
            request=sample_triage_request,
            recall_summary=None,
            enable_memory=False,
        )

        assert mock_provider.call_count == 2
        assert response.is_degraded is True
        assert response.llm_provider == "degraded_memory_only"
        assert "LLM providers unavailable" in (response.degraded_reason or "")


# ---------------------------------------------------------------------------
# Test 5: Bounded Retry Success (Transient Failure Recovers)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retry_success_recovers_without_degraded_mode(sample_triage_request):
    """Verify that a transient error on attempt 1 succeeds on retry without degrading."""
    mock_provider = MockLLMProvider(
        name="mock_retry_success",
        exceptions=[RuntimeError("Temporary 503 upstream connection drop")],
        responses=[VALID_LLM_JSON],
    )

    test_registry = LLMProviderRegistry()
    test_registry.register(mock_provider)

    with patch.object(groq_service, "registry", test_registry), \
         patch.object(settings, "llm_max_retries", 2), \
         patch.object(settings, "llm_retry_initial_delay_seconds", 0.01):

        response = await groq_service.triage_core(
            request=sample_triage_request,
            recall_summary=None,
            enable_memory=False,
        )

        assert mock_provider.call_count == 2
        assert response.is_degraded is False
        assert response.degraded_reason is None
        assert response.llm_provider == "mock_retry_success"
        assert response.recommended_runbook.runbook_id == "RB-PAYMENT-EGRESS-TIMEOUT"


# ---------------------------------------------------------------------------
# Test 6: Primary Provider Failure + Fallback Provider Success
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_primary_provider_failure_and_fallback_success(sample_triage_request):
    """Verify failover to secondary provider when primary fails all retries."""
    primary_provider = MockLLMProvider(
        name="primary_failing",
        exceptions=[
            RuntimeError("Primary Groq API unreachable"),
            RuntimeError("Primary Groq API unreachable"),
        ],
    )
    fallback_provider = MockLLMProvider(
        name="secondary_backup",
        responses=[VALID_LLM_JSON],
    )

    test_registry = LLMProviderRegistry()
    test_registry.register(primary_provider)
    test_registry.register(fallback_provider)

    with patch.object(groq_service, "registry", test_registry), \
         patch.object(settings, "llm_max_retries", 1), \
         patch.object(settings, "llm_retry_initial_delay_seconds", 0.01):

        response = await groq_service.triage_core(
            request=sample_triage_request,
            recall_summary=None,
            enable_memory=False,
        )

        assert primary_provider.call_count == 2
        assert fallback_provider.call_count == 1
        assert response.is_degraded is False
        assert response.degraded_reason is None
        assert response.llm_provider == "secondary_backup"


# ---------------------------------------------------------------------------
# Test 7: All Providers Unavailable Returns 200 DEGRADED Response (No 500)
# ---------------------------------------------------------------------------

def test_all_providers_unavailable_returns_200_degraded(client):
    """Verify that complete provider outage returns HTTP 200 in DEGRADED state, never 500."""
    payload = {
        "service": "order-api",
        "alert": "OrderProcessingQueueStalled",
        "symptoms": ["Queue depth > 50,000", "Worker thread count at max capacity"],
        "severity": "CRITICAL",
        "enable_memory": False,
    }

    # Simulate empty/unavailable provider registry
    empty_registry = LLMProviderRegistry()

    with patch.object(groq_service, "registry", empty_registry):
        response = client.post("/api/triage", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["is_degraded"] is True
        assert data["llm_provider"] == "degraded_memory_only"
        assert "LLM providers unavailable" in data["degraded_reason"]
        assert data["requires_human_approval"] is True
        assert data["recommended_runbook"] is not None


# ---------------------------------------------------------------------------
# Test 8: Degraded Memory-Evidence-Only Response Uses Only Trusted Precedent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_degraded_memory_evidence_only_response_uses_only_verified_precedent(sample_triage_request):
    """Verify that degraded mode strictly uses trusted Hindsight memory and never fabricates."""
    empty_registry = LLMProviderRegistry()

    # Part A: Known Incident with Verified Hindsight Memory Precedent
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
    recall_summary = RecallResultSummary(
        match_strength=MatchStrength.HIGH,
        is_novel=False,
        memories_found=[verified_item],
        evidence_bullets=[
            "Service exact match: payment-api",
            "Matched verified historical incident INC-104",
        ],
        query_used="PaymentGatewayEgressTimeoutBreached",
        hindsight_connected=True,
    )

    with patch.object(groq_service, "registry", empty_registry):
        response = await groq_service.triage_core(
            request=sample_triage_request,
            recall_summary=recall_summary,
            enable_memory=True,
        )

        assert response.is_degraded is True
        assert response.llm_provider == "degraded_memory_only"
        assert response.novelty is False
        assert len(response.historical_matches) == 1
        assert response.historical_matches[0].incident_id == "INC-104"
        assert response.historical_matches[0].root_cause == "Stripe API gateway latency spike caused connection pool exhaustion."
        assert response.recommended_runbook.runbook_id == "RB-PAYMENT-EGRESS-TIMEOUT"
        assert response.recommended_runbook.historical_reference_id == "INC-104"
        assert "Rolling restart of payment pods" in response.failed_mitigations_to_avoid[0]

    # Part B: Novel Incident (Zero Memories Found)
    novel_summary = RecallResultSummary(
        match_strength=MatchStrength.NONE,
        is_novel=True,
        memories_found=[],
        evidence_bullets=["No historical matches found."],
        query_used="PaymentGatewayEgressTimeoutBreached",
        hindsight_connected=True,
    )

    with patch.object(groq_service, "registry", empty_registry):
        novel_response = await groq_service.triage_core(
            request=sample_triage_request,
            recall_summary=novel_summary,
            enable_memory=True,
        )

        assert novel_response.is_degraded is True
        assert novel_response.llm_provider == "degraded_memory_only"
        assert novel_response.novelty is True
        # NEVER fabricate historical matches or confidence
        assert novel_response.historical_matches == []
        assert novel_response.match_strength == "None"
        assert novel_response.recommended_runbook.historical_reference_id is None
        assert novel_response.incident_summary.startswith("No sufficiently relevant historical incident found")
