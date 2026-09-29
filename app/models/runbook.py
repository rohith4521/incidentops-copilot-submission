"""Runbook recommendation, human-in-the-loop approval, and simulation models."""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class ApprovalStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RunbookAction(BaseModel):
    """An individual actionable step or command within a runbook."""
    step_number: int
    name: str
    command: str
    target_component: str
    is_safe_simulation: bool = True
    description: str


class RunbookRecommendation(BaseModel):
    """Recommended remediation plan requiring human approval (Invariant 4)."""
    id: str = Field(default_factory=lambda: f"REC-{uuid4().hex[:8].upper()}")
    runbook_id: str = Field(..., description="Standardized runbook code, e.g., RB-REDIS-FAILOVER")
    title: str = Field(..., description="Human-readable title of runbook")
    justification: str = Field(
        ...,
        description="Clear justification based on historical evidence or first-principles reasoning",
    )
    historical_reference_id: Optional[str] = Field(
        default=None,
        description="Past incident ID that verified this mitigation (e.g. INC-402)",
    )
    blast_radius_analysis: str = Field(
        ...,
        description="Risk assessment, downstream impacts, and fail-safe boundaries",
    )
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING_APPROVAL)
    actions: List[RunbookAction] = Field(default_factory=list)
    approver: Optional[str] = None
    approval_timestamp: Optional[datetime] = None
    approval_notes: Optional[str] = None
    rejection_reason: Optional[str] = None


class RunbookApprovalRequest(BaseModel):
    """Request to approve a proposed runbook."""
    approver: Optional[str] = Field(default=None, description="Client-supplied approver identity (IGNORED/UNTRUSTED)")
    approved_by: Optional[str] = Field(default=None, description="Alternative client-supplied approver (IGNORED/UNTRUSTED)")
    verifier: Optional[str] = Field(default=None, description="Alternative client-supplied verifier (IGNORED/UNTRUSTED)")
    notes: Optional[str] = Field(default=None, description="Approval notes or operational justification")


class RunbookSimulationResult(BaseModel):
    """Output from executing a dry-run simulation of an approved runbook."""
    recommendation_id: str
    runbook_id: str
    simulated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    executed_by: str
    success: bool
    logs: List[str] = Field(default_factory=list)
    projected_recovery_time_minutes: int = 5
    projected_impact: str
