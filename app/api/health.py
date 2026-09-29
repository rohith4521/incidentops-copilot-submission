"""Backward-compatibility health alias for legacy /api/health callers (Phase 7.2).

Canonical health endpoint: GET /api/v1/health (defined in app.api.observability).
This router preserves GET /api/health as a thin alias delegating directly to canonical get_v1_health().
"""

from fastapi import APIRouter
from app.api.observability import get_v1_health

router = APIRouter(prefix="/health", tags=["Health & Diagnostics (Legacy Alias)"])


@router.get("", include_in_schema=False)
async def get_system_health():
    """Thin backward-compatible alias for /api/health delegating to canonical /api/v1/health."""
    return await get_v1_health()
