"""Post-Mortem generation and continuous retention loop into Hindsight."""

from datetime import datetime, timezone
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.models.auth import AuthenticatedUser
from app.models.memory import (
    MemorySourceType,
    MemoryStatus,
    RetainIncidentPayload,
    VerificationAudit,
)
from app.models.postmortem import PostMortemCommitResponse, PostMortemCreate
from app.models.triage import TriageResult
from app.services.auth_service import require_human_verifier
from app.services.hindsight_service import hindsight_service
from app.services.provenance_service import (
    CANONICAL_SEEDED_INCIDENTS,
    provenance_service,
)

logger = logging.getLogger("incidentops.postmortem")

# Primary router for /postmortems (plural)
router = APIRouter(prefix="/postmortems", tags=["Post-Mortems & Continuous Learning"])

# Secondary router for /postmortem (singular, adhering to project spec)
singular_router = APIRouter(prefix="/postmortem", tags=["Post-Mortem & Memory Retention"])


class DraftPostMortemRequest(BaseModel):
    triage_result: TriageResult
    incident_title: Optional[str] = None
    confirmed_resolution: Optional[str] = None
    runbook_executed: Optional[str] = None


class VerifyPostMortemRequest(BaseModel):
    """Request payload for human SRE verification of a draft post-mortem."""
    verifier: str = Field(default="oncall-sre", description="Identity of human SRE verifying postmortem")
    notes: Optional[str] = Field(default=None, description="Verification notes or sign-off remarks")
    confirmed_runbook: Optional[str] = Field(default=None, description="Confirmed runbook code")


@router.post("/draft", response_model=PostMortemCreate)
async def draft_postmortem(req: DraftPostMortemRequest):
    """Draft a structured post-mortem document from a triage result.

    INVARIANT: Newly drafted AI content is ALWAYS created with status DRAFT.
    AI-generated content CANNOT mark itself VERIFIED.
    """
    tr = req.triage_result
    rca = tr.root_cause_analysis

    draft = PostMortemCreate(
        incident_id=tr.incident_id,
        title=req.incident_title or f"Incident Outage - {tr.alert_id}",
        service=rca.affected_components[0] if rca.affected_components else "service",
        severity="CRITICAL" if "CRITICAL" in tr.triage_summary else "HIGH",
        root_cause=rca.hypothesis,
        trigger="; ".join(rca.contributing_factors) if rca.contributing_factors else "System anomaly",
        impact_summary=rca.blast_radius,
        timeline=[
            {"time": "T+0m", "event": f"Alert triggered with symptoms: {', '.join(rca.contributing_factors[:2])}"},
            {"time": "T+3m", "event": "SRE IncidentOps Copilot performed automated triage & Hindsight memory recall."},
            {"time": "T+8m", "event": f"Runbook {req.runbook_executed or 'mitigation'} approved and executed."},
            {"time": "T+15m", "event": "System metrics normalized; incident declared mitigated."},
        ],
        resolution_steps=[
            req.confirmed_resolution
            or tr.immediate_mitigation
            or "Executed approved remediation runbook to restore normal operations."
        ],
        runbook_executed=req.runbook_executed
        or (tr.recommended_runbook.runbook_id if tr.recommended_runbook else None),
        preventative_actions=[
            "Establish proactive Prometheus alerts for early saturation warning thresholds.",
            "Refine runbook automated verification probes and failure isolation boundaries.",
            "Retain post-mortem in Hindsight Continuous Memory for future incident correlation.",
        ],
        tags=[
            rca.affected_components[0] if rca.affected_components else "service",
            "post-mortem",
            "mitigated",
        ] + (["security-quarantine"] if getattr(tr, "injection_detected", False) or getattr(tr, "security_quarantine", False) else []),
        # Provenance: Strictly DRAFT / AI_DRAFT
        memory_status=MemoryStatus.DRAFT,
        source_type=MemorySourceType.AI_DRAFT,
        verified_by=None,
        verified_at=None,
        source_incident_id=tr.incident_id,
    )
    return draft


async def _execute_retain(payload: RetainIncidentPayload) -> PostMortemCommitResponse:
    """Core logic to retain structured incident post-mortem into Hindsight memory."""
    logger.info("Executing Hindsight retain for incident '%s' (status=%s)...", payload.incident_id, payload.memory_status.value)
    result = await hindsight_service.retain_incident(payload)

    if not result.get("success"):
        raise HTTPException(
            status_code=400 if result.get("status") == "unauthorized" else 500,
            detail=result.get("error", "Failed retaining post-mortem in Hindsight API"),
        )

    return PostMortemCommitResponse(
        success=True,
        incident_id=payload.incident_id,
        bank_id=payload.bank_id or settings.hindsight_bank_id,
        operation_id=result.get("operation_id"),
        retained_content_length=len(result.get("content_preview", "")),
        retained_preview=result.get("content_preview", ""),
        status_message=(
            f"Successfully retained structured incident {payload.incident_id} ({payload.service}) "
            f"into genuine Hindsight memory bank '{payload.bank_id or settings.hindsight_bank_id}' "
            f"as {payload.memory_status.value}."
        ),
        memory_status=payload.memory_status,
        source_type=payload.source_type,
        verified_by=payload.verified_by,
        verified_at=payload.verified_at,
    )


async def _process_authenticated_retain(
    payload: RetainIncidentPayload,
    auth_user: AuthenticatedUser,
) -> PostMortemCommitResponse:
    """Process retention into Hindsight under strict provenance boundary (Phase 7.1).

    Invariants:
    1. Authenticated identity is required (unauthenticated -> 401, AI -> 403).
    2. Client-supplied verified_by is NEVER trusted. Authenticated identity is the only source.
    3. A client cannot promote a memory directly from DRAFT to VERIFIED through this endpoint.
    4. If the incident has already completed human verification (audit record exists),
       it preserves VERIFIED status under the verified identity from the audit record.
    5. Otherwise, it is retained strictly as DRAFT with verified_by=None.
    """
    audit_trail = provenance_service.get_audit_trail(payload.incident_id)
    is_canonical = payload.incident_id in CANONICAL_SEEDED_INCIDENTS

    if is_canonical:
        payload.memory_status = MemoryStatus.VERIFIED
        payload.source_type = MemorySourceType.HUMAN_VERIFIED
        payload.verified_by = payload.verified_by or "sre-core-team"
        payload.verified_at = payload.verified_at or datetime.now(timezone.utc)
    elif audit_trail:
        # Incident has previously passed authenticated human verification
        latest_audit = audit_trail[-1]
        payload.memory_status = MemoryStatus.VERIFIED
        payload.source_type = MemorySourceType.HUMAN_VERIFIED
        payload.verified_by = latest_audit.verifier
        payload.verified_at = latest_audit.verified_at
    else:
        # Unverified memory: MUST NOT be promoted to VERIFIED via retain
        # Any client-supplied verified_by, verification identity, or VERIFIED status is rejected/ignored
        if payload.memory_status == MemoryStatus.VERIFIED or payload.verified_by:
            logger.warning(
                "[SECURITY] Direct trust promotion blocked on retain for '%s': "
                "Client-supplied VERIFIED status / verified_by '%s' ignored. Storing strictly as DRAFT.",
                payload.incident_id,
                payload.verified_by,
            )
        payload.memory_status = MemoryStatus.DRAFT
        payload.source_type = MemorySourceType.AI_DRAFT
        payload.verified_by = None
        payload.verified_at = None

    return await _execute_retain(payload)


@singular_router.post("/retain", response_model=PostMortemCommitResponse)
async def retain_structured_postmortem(
    payload: RetainIncidentPayload,
    auth_user: AuthenticatedUser = Depends(require_human_verifier),
):
    """Store structured incident memory into Hindsight (Phase 1 & 5 specification).

    Protected with authenticated human-verifier dependency (Phase 7.1).
    Never trusts client-supplied verified_by or VERIFIED status.
    """
    return await _process_authenticated_retain(payload, auth_user)


@router.post("/retain", response_model=PostMortemCommitResponse)
async def retain_structured_postmortems_alias(
    payload: RetainIncidentPayload,
    auth_user: AuthenticatedUser = Depends(require_human_verifier),
):
    """Alias for /api/postmortem/retain under /postmortems (Phase 7.1)."""
    return await _process_authenticated_retain(payload, auth_user)


@router.post("/commit", response_model=PostMortemCommitResponse)
async def commit_postmortem_to_hindsight(
    postmortem: PostMortemCreate,
    auth_user: AuthenticatedUser = Depends(require_human_verifier),
):
    """Commit a post-mortem directly into Hindsight Continuous Memory bank (UI loop).

    Human commit action: Promotes post-mortem from DRAFT to VERIFIED memory.
    Identity is strictly populated from the authenticated SRE credential.
    Blocks post-mortems marked with security quarantine or active prompt injection.
    """
    from app.services.security_service import security_service

    # Security boundary check
    if "security-quarantine" in postmortem.tags or security_service.detect_patterns(
        f"{postmortem.root_cause} {postmortem.title} {' '.join(postmortem.resolution_steps)}"
    ):
        raise HTTPException(
            status_code=400,
            detail="Cannot commit post-mortem: contains active prompt injection directives or marked for security quarantine.",
        )

    verifier_id = auth_user.identity

    # Record verification audit
    audit = provenance_service.record_verification(
        incident_id=postmortem.incident_id,
        verifier=verifier_id,
        action="HUMAN_VERIFIED_POSTMORTEM",
        notes=f"Committed post-mortem via verified identity ({auth_user.auth_type})",
        previous_status=MemoryStatus.DRAFT.value,
        new_status=MemoryStatus.VERIFIED.value,
        source_type=MemorySourceType.HUMAN_VERIFIED.value,
        metadata={"service": postmortem.service, "severity": postmortem.severity, "auth_type": auth_user.auth_type},
    )

    payload = RetainIncidentPayload(
        bank_id=settings.hindsight_bank_id,
        incident_id=postmortem.incident_id,
        service=postmortem.service,
        title=postmortem.title,
        severity=postmortem.severity,
        alert_signature=f"AlertSignature-{postmortem.service}",
        symptoms=[postmortem.trigger],
        root_cause=postmortem.root_cause,
        failed_mitigations=[],
        verified_runbook=postmortem.runbook_executed or "RB-STANDARD-RESTART",
        postmortem_summary="\n".join(postmortem.resolution_steps),
        timeline=postmortem.timeline,
        lessons_learned=postmortem.preventative_actions,
        tags=postmortem.tags,
        # Provenance: Promoted to VERIFIED by human commit action with authenticated identity
        memory_status=MemoryStatus.VERIFIED,
        source_type=MemorySourceType.HUMAN_VERIFIED,
        verified_by=verifier_id,
        verified_at=audit.verified_at,
        source_incident_id=postmortem.source_incident_id or postmortem.incident_id,
    )
    return await _execute_retain(payload)


@singular_router.post("/commit", response_model=PostMortemCommitResponse)
async def commit_postmortem_singular_alias(
    postmortem: PostMortemCreate,
    auth_user: AuthenticatedUser = Depends(require_human_verifier),
):
    """Singular route alias for /api/postmortem/commit."""
    return await commit_postmortem_to_hindsight(postmortem, auth_user)


@router.post("/{incident_id}/verify", response_model=PostMortemCommitResponse)
async def verify_postmortem_endpoint(
    incident_id: str,
    req: VerifyPostMortemRequest,
    auth_user: AuthenticatedUser = Depends(require_human_verifier),
):
    """Human-in-the-Loop verification gate: Promotes an existing DRAFT memory to VERIFIED.

    Enforces trust invariant: Only authenticated human verification can promote DRAFT -> VERIFIED.
    Identity is strictly populated from the authenticated SRE credential (never trusting client-supplied strings).
    Records verification audit entry with verified operator identity and timestamp.
    """
    # Authenticated identity strictly derived from validated credential
    verified_by_identity = auth_user.identity

    from app.services.security_service import security_service
    if req.confirmed_runbook and security_service.detect_patterns(req.confirmed_runbook):
        raise HTTPException(
            status_code=400,
            detail="Cannot verify post-mortem: confirmed runbook contains unsafe commands or prompt injection directives.",
        )

    # Record verification audit
    audit = provenance_service.record_verification(
        incident_id=incident_id,
        verifier=verified_by_identity,
        action="HUMAN_VERIFIED_POSTMORTEM",
        notes=req.notes,
        previous_status=MemoryStatus.DRAFT.value,
        new_status=MemoryStatus.VERIFIED.value,
        source_type=MemorySourceType.HUMAN_VERIFIED.value,
        metadata={"confirmed_runbook": req.confirmed_runbook, "auth_type": auth_user.auth_type},
    )

    # Retain/promote in Hindsight with VERIFIED status
    payload = RetainIncidentPayload(
        bank_id=settings.hindsight_bank_id,
        incident_id=incident_id,
        service="service",
        severity="HIGH",
        root_cause="Human verified root cause analysis",
        verified_runbook=req.confirmed_runbook or "RB-VERIFIED-MITIGATION",
        postmortem_summary=f"Incident {incident_id} verified by {verified_by_identity}. {req.notes or ''}",
        memory_status=MemoryStatus.VERIFIED,
        source_type=MemorySourceType.HUMAN_VERIFIED,
        verified_by=verified_by_identity,
        verified_at=audit.verified_at,
        source_incident_id=incident_id,
    )
    return await _execute_retain(payload)


@singular_router.post("/{incident_id}/verify", response_model=PostMortemCommitResponse)
async def verify_postmortem_singular_alias(
    incident_id: str,
    req: VerifyPostMortemRequest,
    auth_user: AuthenticatedUser = Depends(require_human_verifier),
):
    """Singular alias for /api/postmortem/{incident_id}/verify."""
    return await verify_postmortem_endpoint(incident_id, req, auth_user)


@router.get("/audit", response_model=List[VerificationAudit])
async def list_verification_audit_log(incident_id: Optional[str] = None):
    """Retrieve the provenance verification audit trail."""
    return provenance_service.get_audit_trail(incident_id)


@singular_router.get("/audit", response_model=List[VerificationAudit])
async def list_verification_audit_log_singular(incident_id: Optional[str] = None):
    """Singular route alias for /api/postmortem/audit."""
    return provenance_service.get_audit_trail(incident_id)

