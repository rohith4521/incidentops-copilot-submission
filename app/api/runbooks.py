"""Human-in-the-Loop runbook approval and dry-run simulation endpoints."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.models.auth import AuthenticatedUser
from app.models.runbook import (
    RunbookApprovalRequest,
    RunbookRecommendation,
    RunbookSimulationResult,
)
from app.services.auth_service import require_human_verifier
from app.services.runbook_service import RunbookApprovalError, runbook_service
from app.services.security_service import security_service

logger = logging.getLogger("incidentops.api.runbooks")

router = APIRouter(prefix="/runbooks", tags=["Runbooks & Human-in-the-Loop"])


class SimulationRequest(BaseModel):
    executor: str = Field(default="oncall-sre", description="SRE username triggering simulation")


class RejectionRequest(BaseModel):
    """Request payload to reject a proposed runbook."""
    approver: Optional[str] = Field(default=None, description="Client-supplied approver identity (IGNORED/UNTRUSTED)")
    rejected_by: Optional[str] = Field(default=None, description="Alternative client-supplied rejector (IGNORED/UNTRUSTED)")
    verifier: Optional[str] = Field(default=None, description="Alternative client-supplied verifier (IGNORED/UNTRUSTED)")
    reason: str = Field(default="Rejected by SRE", description="Technical or operational reason for rejection")
    notes: Optional[str] = Field(default=None, description="Optional rejection notes")


@router.get("", response_model=List[RunbookRecommendation])
async def list_runbook_recommendations():
    """List all registered runbook recommendations and their approval status."""
    return runbook_service.list_recommendations()


@router.get("/{recommendation_id}", response_model=RunbookRecommendation)
async def get_runbook_recommendation(recommendation_id: str):
    """Retrieve specific runbook recommendation by ID."""
    rec = runbook_service.get_recommendation(recommendation_id)
    if not rec:
        raise HTTPException(
            status_code=404,
            detail=f"Runbook recommendation '{recommendation_id}' not found.",
        )
    return rec


@router.post("/{recommendation_id}/approve", response_model=RunbookRecommendation)
async def approve_runbook(
    recommendation_id: str,
    req: RunbookApprovalRequest,
    auth_user: AuthenticatedUser = Depends(require_human_verifier),
):
    """Record human approval for a runbook recommendation.

    Protected with require_human_verifier dependency (Phase 7.4C).
    Requires authenticated human SRE identity (anonymous -> 401, AI -> 403).
    Client-supplied approver, approved_by, or verifier fields are NEVER trusted.
    The effective operator identity is derived exclusively from auth_user.identity.
    """
    operator_identity = auth_user.identity

    # Prompt injection safety check on approval notes
    if req.notes and security_service.detect_patterns(req.notes):
        raise HTTPException(
            status_code=400,
            detail="Cannot approve runbook: approval notes contain unsafe directives or prompt injection patterns.",
        )

    try:
        rec = runbook_service.approve_runbook(
            recommendation_id=recommendation_id,
            approver=operator_identity,
            notes=req.notes,
        )
        return rec
    except KeyError as ke:
        raise HTTPException(status_code=404, detail=str(ke))


@router.post("/{recommendation_id}/reject", response_model=RunbookRecommendation)
async def reject_runbook(
    recommendation_id: str,
    req: RejectionRequest,
    auth_user: AuthenticatedUser = Depends(require_human_verifier),
):
    """Record human rejection for a runbook recommendation.

    Protected with require_human_verifier dependency (Phase 7.4C).
    Requires authenticated human SRE identity (anonymous -> 401, AI -> 403).
    Client-supplied approver, rejected_by, or verifier fields are NEVER trusted.
    The effective operator identity is derived exclusively from auth_user.identity.
    """
    operator_identity = auth_user.identity

    # Prompt injection safety check on rejection reason
    text_to_check = f"{req.reason} {req.notes or ''}"
    if security_service.detect_patterns(text_to_check):
        raise HTTPException(
            status_code=400,
            detail="Cannot reject runbook: rejection reason contains unsafe directives or prompt injection patterns.",
        )

    try:
        rec = runbook_service.reject_runbook(
            recommendation_id=recommendation_id,
            approver=operator_identity,
            reason=req.reason,
        )
        return rec
    except KeyError as ke:
        raise HTTPException(status_code=404, detail=str(ke))


@router.post("/{recommendation_id}/simulate", response_model=RunbookSimulationResult)
async def simulate_runbook(
    recommendation_id: str,
    req: SimulationRequest,
):
    """Execute dry-run simulation of an approved runbook.

    STRICT INVARIANT 4 ENFORCEMENT:
    Returns HTTP 400 Bad Request if human approval has not been granted.
    Preserves purely non-destructive, isolated dry-run simulation behavior.
    """
    try:
        result = runbook_service.simulate_runbook(
            recommendation_id=recommendation_id,
            executor=req.executor,
        )
        return result
    except RunbookApprovalError as rae:
        raise HTTPException(
            status_code=400,
            detail=str(rae),
        )
    except KeyError as ke:
        raise HTTPException(
            status_code=404,
            detail=str(ke),
        )
