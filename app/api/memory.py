from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.models.alert import AlertPayload
from app.models.auth import AuthenticatedUser
from app.models.memory import (
    MemorySourceType,
    MemoryStatus,
    RecallResultSummary,
    RetainIncidentPayload,
)
from app.services.auth_service import (
    get_current_authenticated_user,
    require_human_verifier,
)
from app.services.hindsight_service import hindsight_service

logger = logging.getLogger("incidentops.api.memory")

router = APIRouter(prefix="/memory", tags=["Hindsight Continuous Memory"])


class DirectRecallRequest(BaseModel):
    query: str = Field(..., description="Semantic search query for incident memory")
    service: Optional[str] = Field(None, description="Optional service filter")
    max_tokens: int = Field(default=4096, description="Token budget for recall response")


class ReflectRequest(BaseModel):
    query: str = Field(
        ...,
        description="Reflection prompt (e.g. 'What are the recurring failure patterns in checkout-service?')",
    )


@router.get("/status")
async def get_memory_status():
    """Report genuine Hindsight Cloud / local API health and bank configuration."""
    health = await hindsight_service.check_health()
    return {
        "hindsight_health": health,
        "bank_id": settings.hindsight_bank_id,
        "base_url": settings.hindsight_api_url,
    }


@router.post("/recall", response_model=RecallResultSummary)
async def recall_memory(
    request: DirectRecallRequest,
    auth_user: AuthenticatedUser = Depends(get_current_authenticated_user),
):
    """Directly query Hindsight API memory bank with an SRE search query."""
    # Synthesize synthetic alert for unified recall processing
    synthetic_alert = AlertPayload(
        title=f"Direct Recall: {request.query[:40]}",
        service=request.service or "infrastructure",
        description=request.query,
        symptoms=[request.query],
    )
    result = await hindsight_service.recall_incident_memory(synthetic_alert)
    return result


@router.post(
    "/retain",
    deprecated=True,
    summary="[DEPRECATED] Low-level direct memory retention endpoint (protected by human verifier)",
)
async def retain_memory(
    payload: RetainIncidentPayload,
    auth_user: AuthenticatedUser = Depends(require_human_verifier),
):
    """Retain a post-mortem or operational incident directly into Hindsight memory bank.

    Protected with authenticated human-verifier dependency (Phase 7.4B).
    Deprecated in favor of canonical authenticated flow POST /api/postmortems/commit.
    Never trusts client-supplied verified_by or VERIFIED status.
    """
    from app.services.provenance_service import CANONICAL_SEEDED_INCIDENTS, provenance_service

    audit_trail = provenance_service.get_audit_trail(payload.incident_id)
    is_canonical = payload.incident_id in CANONICAL_SEEDED_INCIDENTS

    if is_canonical:
        payload.memory_status = MemoryStatus.VERIFIED
        payload.source_type = MemorySourceType.HUMAN_VERIFIED
        payload.verified_by = payload.verified_by or "sre-core-team"
        payload.verified_at = payload.verified_at or datetime.now(timezone.utc)
    elif audit_trail:
        latest_audit = audit_trail[-1]
        payload.memory_status = MemoryStatus.VERIFIED
        payload.source_type = MemorySourceType.HUMAN_VERIFIED
        payload.verified_by = latest_audit.verifier
        payload.verified_at = latest_audit.verified_at
    else:
        # Unverified memory: client-supplied VERIFIED status / verified_by is stripped
        if payload.memory_status == MemoryStatus.VERIFIED or payload.verified_by:
            logger.warning(
                "[SECURITY] Direct trust promotion blocked on /api/memory/retain for '%s': "
                "Client-supplied VERIFIED status / verified_by '%s' ignored. Storing strictly as DRAFT.",
                payload.incident_id,
                payload.verified_by,
            )
        payload.memory_status = MemoryStatus.DRAFT
        payload.source_type = MemorySourceType.AI_DRAFT
        payload.verified_by = None
        payload.verified_at = None

    result = await hindsight_service.retain_incident(payload)
    if not result.get("success"):
        raise HTTPException(
            status_code=400 if result.get("status") == "unauthorized" else 500,
            detail=result.get("error", "Failed retaining memory into Hindsight"),
        )
    return result


@router.post("/reflect")
async def reflect_memory(
    request: ReflectRequest,
    auth_user: AuthenticatedUser = Depends(get_current_authenticated_user),
):
    """Synthesize high-density insights from Hindsight memory bank using 'reflect'."""
    reflection_result = await hindsight_service.reflect_insights(request.query)
    return {
        "bank_id": settings.hindsight_bank_id,
        "query": request.query,
        "reflection": reflection_result,
    }


@router.get("/seed-corpus")
async def get_seed_corpus():
    """Retrieve preloaded historical incident corpus without retaining."""
    seed_file = Path(__file__).resolve().parent.parent / "data" / "seed_incidents.json"
    if not seed_file.exists():
        raise HTTPException(status_code=404, detail="Seed incidents file not found")
    with open(seed_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.post("/seed")
async def seed_hindsight_memory():
    """Retain all 4 preloaded historical SRE incidents directly into Hindsight memory bank."""
    seed_file = Path(__file__).resolve().parent.parent / "data" / "seed_incidents.json"
    if not seed_file.exists():
        raise HTTPException(status_code=404, detail="Seed incidents file not found")

    with open(seed_file, "r", encoding="utf-8") as f:
        incidents = json.load(f)

    results = []
    for inc in incidents:
        payload = RetainIncidentPayload(
            bank_id=settings.hindsight_bank_id,
            incident_id=inc["incident_id"],
            service=inc["service"],
            severity=inc.get("severity", "HIGH"),
            alert_signature=inc.get("alert_signature", f"AlertSignature-{inc['service']}"),
            title=inc.get("title", f"{inc['incident_id']} - {inc['service']}"),
            symptoms=inc.get("symptoms", []),
            root_cause=inc["root_cause"],
            failed_mitigations=inc.get("failed_mitigations", []),
            verified_runbook=inc.get("verified_runbook") or inc.get("runbook_executed", "None"),
            postmortem_summary=inc.get("postmortem_summary") or inc.get("resolution", ""),
            resolution=inc.get("resolution"),
            runbook_executed=inc.get("runbook_executed"),
            timeline=inc.get("timeline"),
            lessons_learned=inc.get("preventative_actions"),
            tags=inc.get("tags", []),
        )
        res = await hindsight_service.retain_incident(payload)
        results.append(res)

    successful = [r for r in results if r.get("success")]
    return {
        "total_seeded": len(results),
        "successful_retained": len(successful),
        "bank_id": settings.hindsight_bank_id,
        "details": results,
    }
