"""Triage response and root cause analysis models."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field

import json
from pydantic import field_validator

from app.models.memory import IncidentMemoryItem, MatchStrength
from app.models.runbook import RunbookRecommendation
from app.models.security import (
    CONTROL_CHAR_RE,
    MAX_ALERT_TITLE_LEN,
    MAX_CONTEXT_KEYS,
    MAX_CONTEXT_SERIALIZED_LEN,
    MAX_DESCRIPTION_LEN,
    MAX_SERVICE_LEN,
    MAX_SYMPTOMS_COUNT,
    MAX_SYMPTOM_ITEM_LEN,
)


class RootCauseAnalysis(BaseModel):
    """Deep SRE root cause hypothesis and failure domain breakdown."""
    hypothesis: str = Field(..., description="Primary probable root cause hypothesis")
    contributing_factors: List[str] = Field(default_factory=list)
    blast_radius: str = Field(..., description="Estimated blast radius across systems")
    affected_components: List[str] = Field(default_factory=list)


class HistoricalMatch(BaseModel):
    """Structured historical incident memory match from Hindsight."""
    incident_id: str = Field(..., description="Historical incident identifier, e.g. INC-104")
    service: str = Field(..., description="Affected service name")
    title: Optional[str] = Field(default=None, description="Title of historical incident")
    match_strength: str = Field(default="High", description="Categorical match strength: High or Moderate")
    root_cause: Optional[str] = Field(default=None, description="Documented root cause")
    verified_runbook: Optional[str] = Field(default=None, description="Proven verified mitigation runbook")
    failed_mitigations: List[str] = Field(
        default_factory=list,
        description="Mitigations attempted during outage that failed or aggravated symptoms",
    )
    postmortem_summary: Optional[str] = Field(default=None, description="Post-mortem summary")


class TriageRequest(BaseModel):
    """Input payload for production triage flow POST /api/v1/triage with strict security validation."""
    service: str = Field(..., max_length=MAX_SERVICE_LEN, description="Target service/microservice name")
    alert: Optional[str] = Field(default=None, max_length=MAX_ALERT_TITLE_LEN, description="Alert title or signature")
    signature: Optional[str] = Field(default=None, max_length=MAX_ALERT_TITLE_LEN, description="Alert signature")
    alert_signature: Optional[str] = Field(default=None, max_length=MAX_ALERT_TITLE_LEN, description="Alert signature alias")
    title: Optional[str] = Field(default=None, max_length=MAX_ALERT_TITLE_LEN, description="Alert headline/title alias")
    description: Optional[str] = Field(default=None, description="Detailed alert description")
    symptoms: Any = Field(default_factory=list, description="Observed operational symptoms (list or string)")
    severity: str = Field(default="HIGH", max_length=32, description="Alert severity: CRITICAL, HIGH, MEDIUM, LOW")
    context: Optional[Any] = Field(default=None, description="Optional diagnostic or environment context")
    enable_memory: bool = Field(default=True, description="Enable continuous memory recall via Hindsight")
    model: Optional[str] = Field(default=None, description="Optional Groq model override")

    @field_validator("service", "alert", "signature", "alert_signature", "title", "severity", mode="before")
    @classmethod
    def sanitize_short_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            # Normalize control characters and strip whitespace
            return CONTROL_CHAR_RE.sub("", v).strip()
        return v

    @field_validator("description", mode="before")
    @classmethod
    def validate_and_sanitize_description(cls, v: Any) -> Any:
        if v is None:
            return None
        if not isinstance(v, str):
            v = str(v)
        # Check oversized before or after cleaning
        cleaned = CONTROL_CHAR_RE.sub("", v).strip()
        if len(cleaned) > MAX_DESCRIPTION_LEN:
            raise ValueError(f"Alert description exceeds maximum allowed length of {MAX_DESCRIPTION_LEN} characters (got {len(cleaned)}).")
        return cleaned

    @field_validator("symptoms", mode="before")
    @classmethod
    def validate_and_sanitize_symptoms(cls, v: Any) -> Any:
        if v is None:
            return []
        if isinstance(v, str):
            cleaned = CONTROL_CHAR_RE.sub("", v).strip()
            if len(cleaned) > MAX_DESCRIPTION_LEN:
                raise ValueError(f"Symptoms string exceeds maximum allowed length of {MAX_DESCRIPTION_LEN} characters.")
            return cleaned
        if isinstance(v, list):
            if len(v) > MAX_SYMPTOMS_COUNT:
                raise ValueError(f"Symptoms list exceeds maximum allowed count of {MAX_SYMPTOMS_COUNT} items (got {len(v)}).")
            cleaned_list = []
            for item in v:
                s_item = str(item)
                cleaned_item = CONTROL_CHAR_RE.sub("", s_item).strip()
                if len(cleaned_item) > MAX_SYMPTOM_ITEM_LEN:
                    raise ValueError(f"Individual symptom item exceeds maximum allowed length of {MAX_SYMPTOM_ITEM_LEN} characters.")
                cleaned_list.append(cleaned_item)
            return cleaned_list
        return v

    @field_validator("context", mode="before")
    @classmethod
    def validate_and_sanitize_context(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, str):
            cleaned = CONTROL_CHAR_RE.sub("", v).strip()
            if len(cleaned) > MAX_CONTEXT_SERIALIZED_LEN:
                raise ValueError(f"Context string exceeds maximum allowed length of {MAX_CONTEXT_SERIALIZED_LEN} characters.")
            return cleaned
        if isinstance(v, dict):
            if len(v) > MAX_CONTEXT_KEYS:
                raise ValueError(f"Context object exceeds maximum allowed key count of {MAX_CONTEXT_KEYS} (got {len(v)}).")
            serialized = json.dumps(v)
            if len(serialized) > MAX_CONTEXT_SERIALIZED_LEN:
                raise ValueError(f"Context serialized size exceeds maximum allowed limit of {MAX_CONTEXT_SERIALIZED_LEN} bytes.")
            return v
        if isinstance(v, list):
            serialized = json.dumps(v)
            if len(serialized) > MAX_CONTEXT_SERIALIZED_LEN:
                raise ValueError(f"Context serialized size exceeds maximum allowed limit of {MAX_CONTEXT_SERIALIZED_LEN} bytes.")
            return v
        return v

    @property
    def alert_title(self) -> str:
        return (
            self.alert
            or self.signature
            or self.alert_signature
            or self.title
            or f"{self.service} Alert"
        )

    @property
    def normalized_symptoms(self) -> List[str]:
        if isinstance(self.symptoms, str):
            stripped = self.symptoms.strip()
            return [stripped] if stripped else []
        if isinstance(self.symptoms, list):
            return [str(s) for s in self.symptoms if str(s).strip()]
        return []


class TriageResponse(BaseModel):
    """Production-quality incident triage response adhering to Phase 2 contract."""
    incident_summary: str = Field(..., description="Executive summary of the incident")
    likely_root_cause: str = Field(..., description="Primary probable root cause hypothesis")
    supporting_evidence: List[str] = Field(default_factory=list, description="Factual evidence bullets")
    historical_matches: List[HistoricalMatch] = Field(
        default_factory=list,
        description="Matched historical incidents from Hindsight. Empty if novel or memory disabled.",
    )
    recommended_runbook: Optional[RunbookRecommendation] = Field(
        default=None,
        description="Recommended runbook requiring human approval before simulation/execution",
    )
    failed_mitigations_to_avoid: List[str] = Field(
        default_factory=list,
        description="Historically proven failed mitigations or anti-patterns to explicitly avoid",
    )
    reasoning_summary: str = Field(..., description="SRE reasoning explanation")
    requires_human_approval: bool = Field(
        default=True,
        description="Strictly True: runbooks require human approval before execution (Invariant 4)",
    )
    memory_used: bool = Field(..., description="True if Hindsight memory was recalled and utilized")
    novelty: bool = Field(..., description="True if incident is novel without historical match or in stateless mode")
    # Separated candidate tracing fields
    candidates_recalled: List[HistoricalMatch] = Field(
        default_factory=list,
        description="Raw candidates retrieved from Hindsight before failure-mode relevance gating",
    )
    relevance_verdict: Optional[str] = Field(
        default=None,
        description="Relevance classification: ACCEPTED, REJECTED_DIFFERENT_FAILURE_MODE, or NONE",
    )
    # Reliability & Degraded Mode fields (Phase 6.1 & Phase 6.2A)
    is_degraded: bool = Field(
        default=False,
        description="True if inference or memory operated in degraded mode",
    )
    degraded_reason: Optional[str] = Field(
        default=None,
        description="Detailed explanation if operating in degraded mode",
    )
    degradation_reason: Optional[str] = Field(
        default=None,
        description="Explicit degradation reason (e.g. 'hindsight_unavailable')",
    )
    memory_available: bool = Field(
        default=True,
        description="False if Hindsight connection, API, or timeout failure occurred",
    )
    llm_provider: Optional[str] = Field(
        default=None,
        description="Provider that handled inference (e.g. 'groq', 'fallback', 'degraded_memory_only')",
    )
    # Prompt Injection Defense & Provenance Quarantine fields (Phase 6.4A)
    injection_detected: bool = Field(
        default=False,
        description="True if prompt injection directives were detected in alert payload",
    )
    security_quarantine: bool = Field(
        default=False,
        description="True if alert contains hostile directives requiring memory quarantine",
    )
    sanitization_applied: bool = Field(
        default=False,
        description="True if input normalization or command defusing was applied",
    )
    # Compatibility aliases
    incident_id: Optional[str] = None
    match_strength: Optional[str] = None


class TriageResult(BaseModel):
    """End-to-end incident triage report synthesized by Groq + Hindsight (Compatibility Model)."""
    incident_id: str = Field(default_factory=lambda: f"INC-{uuid4().hex[:6].upper()}")
    alert_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    match_strength: MatchStrength = Field(
        ...,
        description="Truthful categorical match strength: High, Moderate, or None",
    )
    novelty_detected: bool = Field(
        ...,
        description="True if this is a novel failure mode requiring fresh reasoning",
    )
    evidence_bullets: List[str] = Field(
        default_factory=list,
        description="Verifiable factual bullets linking alert symptoms to recalled memory",
    )
    triage_summary: str = Field(
        ...,
        description="Executive incident triage headline. If novel: starts with 'No sufficiently relevant historical incident found'",
    )
    root_cause_analysis: RootCauseAnalysis
    immediate_mitigation: str
    recommended_runbook: Optional[RunbookRecommendation] = None
    recalled_memories: List[IncidentMemoryItem] = Field(default_factory=list)
    model_used: str = Field(default="llama-3.3-70b-versatile")
    hindsight_telemetry: Dict[str, Any] = Field(default_factory=dict)
