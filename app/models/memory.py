"""Memory models interface for Hindsight Cloud and local instances."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MatchStrength(str, Enum):
    """Categorical match strength adhering to Truthful Metrics (Invariant 3).

    Strictly no uncalculated numerical confidence (e.g. 92%).
    """
    HIGH = "High"
    MODERATE = "Moderate"
    NONE = "None"


class MemoryStatus(str, Enum):
    """Lifecycle status of incident memory items."""
    DRAFT = "DRAFT"
    VERIFIED = "VERIFIED"


class MemorySourceType(str, Enum):
    """Origin source of incident memory content."""
    AI_DRAFT = "AI_DRAFT"
    HUMAN_VERIFIED = "HUMAN_VERIFIED"


class VerificationAudit(BaseModel):
    """Audit entry documenting human verification of incident memory (Phase 7.3A)."""
    incident_id: str = Field(..., description="Unique incident ID")
    verifier: str = Field(default="oncall-sre", description="Identifier of human SRE who verified")
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    action: str = Field(default="HUMAN_VERIFIED_POSTMORTEM", description="Audit action")
    notes: Optional[str] = Field(default=None, description="Verification notes or justification")
    previous_status: Optional[str] = Field(default="DRAFT", description="Previous status (e.g. DRAFT)")
    new_status: str = Field(default="VERIFIED", description="New status (e.g. VERIFIED)")
    source_type: str = Field(default="HUMAN_VERIFIED", description="Source type (e.g. HUMAN_VERIFIED)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Relevant audit metadata")


class IncidentMemoryItem(BaseModel):
    """An incident or operational observation recalled from Hindsight memory."""
    id: str
    incident_id: Optional[str] = None
    service: Optional[str] = None
    severity: Optional[str] = None
    alert_signature: Optional[str] = None
    title: Optional[str] = None
    symptoms: List[str] = Field(default_factory=list)
    root_cause: Optional[str] = None
    failed_mitigations: List[str] = Field(default_factory=list)
    verified_runbook: Optional[str] = None
    postmortem_summary: Optional[str] = None
    # Compatibility aliases
    resolution: Optional[str] = None
    runbook_used: Optional[str] = None
    raw_text: str = ""
    scores: Optional[Dict[str, float]] = None
    tags: List[str] = Field(default_factory=list)
    occurred_at: Optional[str] = None
    # Provenance fields
    memory_status: MemoryStatus = Field(default=MemoryStatus.VERIFIED, description="DRAFT or VERIFIED")
    source_type: MemorySourceType = Field(default=MemorySourceType.HUMAN_VERIFIED, description="AI_DRAFT or HUMAN_VERIFIED")
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None
    source_incident_id: Optional[str] = None


class RecallResultSummary(BaseModel):
    """Summarized recall evaluation outcome from Hindsight memory bank."""
    match_strength: MatchStrength = Field(
        ...,
        description="Categorical Match Strength: High, Moderate, or None",
    )
    is_novel: bool = Field(
        ...,
        description="True if no sufficiently relevant historical incident exists",
    )
    memories_found: List[IncidentMemoryItem] = Field(default_factory=list)
    evidence_bullets: List[str] = Field(
        default_factory=list,
        description="Verifiable factual bullets linking alert symptoms to recalled memory",
    )
    raw_recall_count: int = 0
    query_used: str
    hindsight_connected: bool = True
    diagnostic_note: Optional[str] = None
    # Separated candidate tracing fields
    candidates_retrieved: List[IncidentMemoryItem] = Field(
        default_factory=list,
        description="Raw candidates retrieved from Hindsight before relevance gating",
    )
    relevance_verdict: Optional[str] = Field(
        default=None,
        description="Decision: ACCEPTED, REJECTED_DIFFERENT_FAILURE_MODE, or NONE",
    )
    relevance_reason: Optional[str] = Field(
        default=None,
        description="Detailed explanation for acceptance or rejection by relevance gate",
    )


class RetainIncidentPayload(BaseModel):
    """Payload to retain an incident memory into Hindsight continuous memory.

    Contains all required structured incident memory fields:
    incident_id, service, severity, alert_signature, symptoms, root_cause,
    failed_mitigations, verified_runbook, postmortem_summary.
    """
    bank_id: Optional[str] = None
    incident_id: str = Field(..., description="Unique incident ID (e.g. INC-104)")
    service: str = Field(..., description="Affected service name (e.g. payment-api)")
    severity: str = Field(default="HIGH", description="Severity level: CRITICAL, HIGH, MEDIUM, LOW")
    alert_signature: str = Field(default="", description="Alert trigger signature or rule name")
    title: Optional[str] = Field(default=None, description="Descriptive headline for incident")
    symptoms: List[str] = Field(default_factory=list, description="Observed operational symptoms")
    root_cause: str = Field(..., description="Confirmed root cause analysis")
    failed_mitigations: List[str] = Field(
        default_factory=list,
        description="Mitigations attempted during outage that failed or made it worse",
    )
    verified_runbook: str = Field(..., description="Runbook code/name that definitively mitigated the incident")
    postmortem_summary: str = Field(..., description="High-density post-mortem summary for future recall")
    # Compatibility fields
    resolution: Optional[str] = None
    runbook_executed: Optional[str] = None
    timeline: Optional[List[Dict[str, str]]] = None
    lessons_learned: Optional[List[str]] = None
    tags: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Provenance fields
    memory_status: MemoryStatus = Field(default=MemoryStatus.DRAFT, description="DRAFT or VERIFIED")
    source_type: MemorySourceType = Field(default=MemorySourceType.AI_DRAFT, description="AI_DRAFT or HUMAN_VERIFIED")
    verified_by: Optional[str] = Field(default=None, description="Identity of human verifier")
    verified_at: Optional[datetime] = Field(default=None, description="Timestamp of human verification")
    source_incident_id: Optional[str] = Field(default=None, description="Original incident ID")
