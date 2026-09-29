"""API Router registrations for IncidentOps Copilot."""

from fastapi import APIRouter
from app.api.alerts import router as alerts_router
from app.api.health import router as health_router
from app.api.memory import router as memory_router
from app.api.postmortems import (
    router as postmortems_router,
    singular_router as postmortem_singular_router,
)
from app.api.runbooks import router as runbooks_router
from app.api.triage import (
    router as triage_router,
    legacy_router as triage_legacy_router,
)
from app.api.webhook import router as webhook_router
from app.api.observability import router as observability_router

api_router = APIRouter(prefix="/api")
api_router.include_router(observability_router)
api_router.include_router(health_router)
api_router.include_router(alerts_router)
api_router.include_router(memory_router)
api_router.include_router(runbooks_router)
api_router.include_router(postmortems_router)
api_router.include_router(postmortem_singular_router)
api_router.include_router(triage_router)
api_router.include_router(triage_legacy_router)
api_router.include_router(webhook_router)

__all__ = ["api_router"]
