"""Production incident triage API route (Phase 7.2 Canonical Routing).

Canonical endpoint: POST /api/v1/triage
Legacy compatibility alias: POST /api/triage
"""

import logging
from fastapi import APIRouter, HTTPException
from app.models.triage import TriageRequest, TriageResponse
from app.services.triage_engine import triage_engine

logger = logging.getLogger("incidentops.api.triage")

# Canonical router mounted at /v1 under /api (resulting in /api/v1/triage)
router = APIRouter(prefix="/v1", tags=["Incident Triage (Canonical)"])

# Legacy router mounted under /api (resulting in /api/triage)
legacy_router = APIRouter(tags=["Incident Triage (Legacy Alias)"])


@router.post("/triage", response_model=TriageResponse)
async def triage_incident(request: TriageRequest) -> TriageResponse:
    """Canonical production-quality SRE incident triage flow (POST /api/v1/triage).

    Supports:
    - enable_memory=true: Genuine continuous memory recall via Hindsight API + SRE inference.
    - enable_memory=false: Stateless first-principles triage (Hindsight completely bypassed).
    - Novelty detection: When no historical match exists, novelty=True without fabricating history.
    - Truthful metrics: Categorical match strength, zero fake confidence percentages.
    - Human-in-the-loop: Recommended runbooks strictly require human approval (requires_human_approval=True).
    """
    try:
        return await triage_engine.triage(request)
    except Exception as e:
        logger.error("Triage endpoint error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Triage execution failed: {str(e)}",
        )


@legacy_router.post("/triage", response_model=TriageResponse, include_in_schema=False)
async def triage_incident_legacy_alias(request: TriageRequest) -> TriageResponse:
    """Thin backward-compatible alias for /api/triage delegating directly to canonical /api/v1/triage."""
    return await triage_incident(request)
