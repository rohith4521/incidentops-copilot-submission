"""Post-mortem models completing the continuous learning loop (Invariant 5)."""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


from app.models.memory import MemorySourceType, MemoryStatus


class PostMortemCreate(BaseModel):
    """Structured post-mortem document for continuous retention into Hindsight."""
    incident_id: str = Field(..., description="Unique incident reference (e.g. INC-402)")
    title: str = Field(..., description="Incident title")
    service: str = Field(..., description="Affected service name")
    severity: str = Field(..., description="Incident severity level")
    root_cause: str = Field(..., description="Confirmed root cause analysis")
    trigger: str = Field(..., description="Direct triggering event or condition")
    impact_summary: str = Field(..., description="User or system impact summary")
    timeline: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Key chronological timeline entries (e.g. [{'time': '10:00', 'event': '...' }])",
    )
    resolution_steps: List[str] = Field(
        default_factory=list,
        description="Concrete steps taken that resolved the outage",
    )
    runbook_executed: Optional[str] = Field(
        default=None,
        description="Code or title of runbook executed",
    )
    preventative_actions: List[str] = Field(
        default_factory=list,
        description="Action items and preventative architectural changes",
    )
    tags: List[str] = Field(default_factory=list)
    # Provenance fields
    memory_status: MemoryStatus = Field(default=MemoryStatus.DRAFT, description="Status of the postmortem (DRAFT or VERIFIED)")
    source_type: MemorySourceType = Field(default=MemorySourceType.AI_DRAFT, description="Origin: AI_DRAFT or HUMAN_VERIFIED")
    verified_by: Optional[str] = Field(default=None, description="Identity of human verifier")
    verified_at: Optional[datetime] = Field(default=None, description="Timestamp of human verification")
    source_incident_id: Optional[str] = Field(default=None, description="Original incident ID")


class PostMortemCommitResponse(BaseModel):
    """Result returned after committing post-mortem into Hindsight continuous memory."""
    success: bool
    incident_id: str
    bank_id: str
    operation_id: Optional[str] = None
    retained_content_length: int
    retained_preview: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status_message: str
    # Provenance fields
    memory_status: MemoryStatus = Field(default=MemoryStatus.VERIFIED, description="Status in memory: VERIFIED or DRAFT")
    source_type: MemorySourceType = Field(default=MemorySourceType.HUMAN_VERIFIED, description="AI_DRAFT or HUMAN_VERIFIED")
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None

