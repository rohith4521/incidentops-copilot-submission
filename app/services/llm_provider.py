"""LLM Provider Abstraction and Failover Management.

Decouples incident triage orchestration from specific LLM providers (e.g. Groq),
supporting multiple providers, configurable timeouts, bounded retries with
exponential backoff, and fallback provider chains.
"""

from abc import ABC, abstractmethod
import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional
from groq import AsyncGroq
from groq import APIConnectionError, RateLimitError, APIStatusError

from app.config import settings
from app.models.llm import (
    LLMMalformedJsonError,
    LLMSchemaValidationError,
    LLMTimeoutError,
    LLMTriageOutputSchema,
)

logger = logging.getLogger("incidentops.llm")


# ---------------------------------------------------------------------------
# Base LLM Provider Interface
# ---------------------------------------------------------------------------

class BaseLLMProvider(ABC):
    """Abstract base class for all LLM inference providers."""

    name: str = "base"

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this provider is configured with valid credentials and enabled."""
        pass

    @abstractmethod
    async def generate_triage_json(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> str:
        """Call the provider API and return raw JSON string response.

        Raises:
            LLMTimeoutError: If the request exceeds the configured timeout.
            Exception: On underlying network, authentication, or rate limit failures.
        """
        pass


# ---------------------------------------------------------------------------
# Groq Provider Implementation
# ---------------------------------------------------------------------------

class GroqProvider(BaseLLMProvider):
    """Inference provider implementation using the Groq API (Llama 3.3, Qwen 2.5)."""

    name: str = "groq"

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        client_factory: Optional[Callable[[], Optional[AsyncGroq]]] = None,
    ):
        self.api_key = api_key if api_key is not None else settings.groq_api_key
        self.default_model = default_model or settings.groq_model
        self.client_factory = client_factory

    @property
    def is_available(self) -> bool:
        if self.client_factory:
            try:
                c = self.client_factory()
                return c is not None
            except Exception:
                return True
        return bool(self.api_key and self.api_key.strip())

    def _get_client(self) -> Optional[AsyncGroq]:
        if self.client_factory:
            return self.client_factory()
        if not self.is_available or not self.api_key:
            return None
        return AsyncGroq(api_key=self.api_key.strip())

    async def generate_triage_json(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> str:
        client = self._get_client()
        if not client:
            raise RuntimeError("Groq API key not configured or empty.")

        active_model = model or self.default_model
        req_timeout = timeout or settings.llm_timeout_seconds

        logger.info("Executing Groq inference (model: '%s', timeout: %.1fs)...", active_model, req_timeout)

        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=active_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"},
                ),
                timeout=req_timeout,
            )
            content = response.choices[0].message.content or "{}"
            return content
        except asyncio.TimeoutError:
            logger.warning("Groq inference timed out after %.1fs.", req_timeout)
            raise LLMTimeoutError(self.name, req_timeout)
        except (APIConnectionError, RateLimitError, APIStatusError) as ge:
            logger.error("Groq API error (%s): %s", type(ge).__name__, ge)
            raise


# ---------------------------------------------------------------------------
# Fallback / Secondary Provider Implementation
# ---------------------------------------------------------------------------

class FallbackProvider(BaseLLMProvider):
    """Configurable fallback provider invoked when primary LLM fails.

    Supports custom handlers or secondary backup LLM engines to ensure
    continuous operational availability without unhandled failures.
    """

    name: str = "fallback"

    def __init__(
        self,
        handler: Optional[Callable[..., Any]] = None,
        enabled: bool = True,
        name: str = "fallback",
    ):
        self.handler = handler
        self.enabled = enabled
        self.name = name

    @property
    def is_available(self) -> bool:
        return self.enabled and self.handler is not None

    async def generate_triage_json(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> str:
        req_timeout = timeout or settings.llm_timeout_seconds
        logger.info("Executing Fallback LLM inference (timeout: %.1fs)...", req_timeout)

        if self.handler:
            try:
                res = self.handler(system_prompt=system_prompt, user_prompt=user_prompt, model=model)
                if asyncio.iscoroutine(res):
                    res = await asyncio.wait_for(res, timeout=req_timeout)
                if isinstance(res, dict):
                    return json.dumps(res)
                return str(res)
            except asyncio.TimeoutError:
                raise LLMTimeoutError(self.name, req_timeout)

        # Default fallback synthesis: structured diagnostic response
        fallback_data = {
            "incident_summary": "Incident triage synthesized via secondary fallback engine.",
            "likely_root_cause": "Telemetry indicates transient service degradation or resource saturation.",
            "supporting_evidence": ["Fallback inference engine engaged after primary provider failure."],
            "recommended_runbook": {
                "runbook_id": "RB-FALLBACK-DIAGNOSTIC",
                "title": "Fallback System Diagnostic & Isolation",
                "justification": "Automated safe diagnostic plan generated by fallback engine.",
                "actions": [
                    {
                        "step_number": 1,
                        "name": "Verify Pod & Service Status",
                        "command": "kubectl get pods -o wide",
                        "is_safe_simulation": True,
                        "description": "Inspect pod states and restart counters.",
                    }
                ],
            },
            "failed_mitigations_to_avoid": [
                "Avoid rolling restarts without shedding incoming client traffic."
            ],
            "reasoning_summary": "Analysis generated via secondary fallback provider.",
        }
        return json.dumps(fallback_data)


def _clean_json_text(text: str) -> str:
    """Strip markdown code block fences if returned by LLMs."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


# ---------------------------------------------------------------------------
# LLM Provider Registry & Orchestrator
# ---------------------------------------------------------------------------

class LLMProviderRegistry:
    """Manages ordered list of providers, executing retries and failovers."""

    def __init__(self):
        self._providers: List[BaseLLMProvider] = []

    def register(self, provider: BaseLLMProvider) -> None:
        """Register a provider (added to evaluation priority queue)."""
        self._providers.append(provider)

    def get_providers(self) -> List[BaseLLMProvider]:
        return list(self._providers)

    def clear(self) -> None:
        self._providers.clear()

    async def execute_with_resilience(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        initial_backoff: Optional[float] = None,
    ) -> tuple[LLMTriageOutputSchema, str]:
        """Execute LLM inference with bounded retries and provider failover.

        For each available provider:
          1. Attempts inference with bounded retries & exponential backoff.
          2. Validates JSON parsing and Pydantic schema conformance.
          3. If successful, returns (validated_output, provider_name).
          4. If retries exhausted or fatal error, cascades to next provider.

        Returns:
            Tuple of (LLMTriageOutputSchema, winning_provider_name)

        Raises:
            AllLLMProvidersFailedError: If all providers fail.
        """
        retries_limit = max_retries if max_retries is not None else settings.llm_max_retries
        backoff_base = initial_backoff if initial_backoff is not None else settings.llm_retry_initial_delay_seconds
        req_timeout = timeout if timeout is not None else settings.llm_timeout_seconds

        available_providers = [p for p in self._providers if p.is_available]
        if not available_providers:
            raise RuntimeError("No LLM providers are currently configured or available.")

        provider_errors: Dict[str, str] = {}

        for provider in available_providers:
            logger.info("Attempting LLM inference with provider '%s'...", provider.name)
            current_delay = backoff_base

            for attempt in range(retries_limit + 1):
                try:
                    t_llm_start = asyncio.get_event_loop().time()
                    try:
                        raw_text = await asyncio.wait_for(
                            provider.generate_triage_json(
                                system_prompt=system_prompt,
                                user_prompt=user_prompt,
                                model=model,
                                timeout=req_timeout,
                            ),
                            timeout=req_timeout,
                        )
                    except asyncio.TimeoutError:
                        raise LLMTimeoutError(provider.name, req_timeout)

                    # Step 1: Clean and Parse JSON
                    cleaned_text = _clean_json_text(raw_text)
                    try:
                        parsed_json = json.loads(cleaned_text)
                    except (json.JSONDecodeError, TypeError) as jde:
                        raise LLMMalformedJsonError(provider.name, raw_text, str(jde))

                    # Step 2: Validate against Pydantic schema
                    try:
                        validated = LLMTriageOutputSchema.model_validate(parsed_json)
                    except Exception as ve:
                        raise LLMSchemaValidationError(provider.name, str(ve))

                    llm_dur_ms = (asyncio.get_event_loop().time() - t_llm_start) * 1000
                    from app.services.metrics_service import metrics_service
                    metrics_service.record_llm_latency(llm_dur_ms)

                    logger.info("LLM provider '%s' succeeded on attempt %d/%d.", provider.name, attempt + 1, retries_limit + 1)
                    return validated, provider.name

                except Exception as err:
                    err_msg = str(err)
                    logger.warning(
                        "LLM provider '%s' attempt %d/%d failed: %s",
                        provider.name,
                        attempt + 1,
                        retries_limit + 1,
                        err_msg,
                    )

                    # Check for non-retriable authentication errors to fail fast to next provider
                    is_unretriable_auth = isinstance(err, APIStatusError) and getattr(err, "status_code", None) in (401, 403)
                    if is_unretriable_auth:
                        from app.services.metrics_service import metrics_service
                        metrics_service.inc_llm_failures()
                        provider_errors[provider.name] = f"Authentication failure ({err_msg})"
                        break

                    from app.services.metrics_service import metrics_service
                    if attempt < retries_limit:
                        metrics_service.inc_llm_retries()
                        await asyncio.sleep(current_delay)
                        current_delay *= 2.0
                    else:
                        metrics_service.inc_llm_failures()
                        provider_errors[provider.name] = f"Retries exhausted ({err_msg})"

        from app.services.metrics_service import metrics_service
        metrics_service.inc_llm_failures()
        from app.models.llm import AllLLMProvidersFailedError
        raise AllLLMProvidersFailedError(provider_errors)


# Default global registry singleton with standard providers
provider_registry = LLMProviderRegistry()
provider_registry.register(GroqProvider())
provider_registry.register(FallbackProvider())
