"""API endpoints for System Health and Observability Metrics (Phase 6.8A).

Provides:
- GET /api/v1/health (dependency health status for API, Hindsight, and LLM)
- GET /api/v1/metrics (process-local operational counters and latency metrics)
"""

from datetime import datetime, timezone
import time
from fastapi import APIRouter
from app.config import settings
from app.services.hindsight_service import hindsight_service
from app.services.llm_provider import provider_registry
from app.services.metrics_service import metrics_service

router = APIRouter(prefix="/v1", tags=["Observability & Diagnostics"])

_START_TIME = time.time()


@router.get("/health")
async def get_v1_health():
    """Verify live dependency status for API, Hindsight memory layer, and LLM provider."""
    # 1. API process status
    uptime_sec = round(time.time() - _START_TIME, 2)
    api_health = {
        "status": "healthy",
        "version": "1.0.0",
        "uptime_seconds": uptime_sec,
    }

    # 2. Hindsight dependency status
    hindsight_raw = await hindsight_service.check_health()
    hindsight_status = hindsight_raw.get("status", "unknown")
    cb_status = hindsight_service.circuit_breaker.get_status()
    hindsight_is_ok = hindsight_status in ("connected", "healthy") and not hindsight_service.circuit_breaker.is_open

    hindsight_health = {
        "status": "circuit_open" if hindsight_service.circuit_breaker.is_open else ("connected" if hindsight_is_ok else "unreachable"),
        "endpoint": settings.hindsight_api_url,
        "bank_id": settings.hindsight_bank_id,
        "authenticated": bool(settings.is_hindsight_configured),
        "circuit_breaker": cb_status,
        "details": hindsight_raw,
    }

    # 3. LLM provider dependency status
    available_providers = [p.name for p in provider_registry.get_providers() if p.is_available]
    llm_health = {
        "status": "configured" if settings.is_groq_configured else "fallback",
        "primary_provider": "groq",
        "model": settings.groq_model,
        "configured": bool(settings.is_groq_configured),
        "available_providers": available_providers,
    }

    # Aggregate overall system health
    overall_status = "healthy"
    if not hindsight_is_ok or hindsight_service.circuit_breaker.is_open:
        overall_status = "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dependencies": {
            "api": api_health,
            "hindsight": hindsight_health,
            "llm_provider": llm_health,
        },
        # Backward-compatible top-level properties
        "bank_id": settings.hindsight_bank_id,
        "environment": settings.environment,
        "hindsight": hindsight_health,
        "groq": {
            "status": llm_health["status"],
            "configured": llm_health["configured"],
            "default_model": llm_health["model"],
        },
        "invariants_enforced": [
            "REPO_FIRST",
            "GENUINE_MEMORY_LAYER",
            "TRUTHFUL_METRICS",
            "HUMAN_IN_THE_LOOP",
            "NOVELTY_HANDLING",
            "HYGIENE_AND_RESILIENCE",
        ],
    }


@router.get("/metrics")
async def get_v1_metrics():
    """Return process-local operational metrics, error rates, and latency percentiles."""
    return metrics_service.get_metrics()
