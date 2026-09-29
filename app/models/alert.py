"""Alert models for incoming incident telemetry and alerts."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field, field_validator

from app.models.security import (
    CONTROL_CHAR_RE,
    MAX_ALERT_TITLE_LEN,
    MAX_DESCRIPTION_LEN,
    MAX_SERVICE_LEN,
    MAX_SYMPTOMS_COUNT,
    MAX_SYMPTOM_ITEM_LEN,
)


class AlertSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class AlertSource(str, Enum):
    PROMETHEUS = "Prometheus"
    DATADOG = "Datadog"
    PAGERDUTY = "PagerDuty"
    CLOUDWATCH = "CloudWatch"
    GRAFANA = "Grafana"
    MANUAL = "Manual"


class AlertPayload(BaseModel):
    """Normalized payload representing an operational alert with strict security validation."""
    id: str = Field(default_factory=lambda: f"ALT-{uuid4().hex[:8].upper()}")
    title: str = Field(..., max_length=MAX_ALERT_TITLE_LEN, description="Short, descriptive alert headline")
    service: str = Field(..., max_length=MAX_SERVICE_LEN, description="Target service/microservice name")
    environment: str = Field(default="production", max_length=64, description="Environment (e.g. production, staging)")
    severity: AlertSeverity = Field(default=AlertSeverity.HIGH)
    source: AlertSource = Field(default=AlertSource.PROMETHEUS)
    description: str = Field(..., description="Detailed description of the trigger condition")
    symptoms: List[str] = Field(default_factory=list, description="Observed system symptoms")
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key observability metrics (e.g. error_rate, latency, cpu, memory)",
    )
    cluster: Optional[str] = Field(default="k8s-prod-us-east-1", max_length=128, description="Infrastructure cluster/region")
    runbook_hint: Optional[str] = Field(default=None, max_length=256, description="Suggested or historical runbook tag if known")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("title", "service", "environment", "cluster", "runbook_hint", mode="before")
    @classmethod
    def sanitize_short_fields(cls, v: Any) -> Any:
        if isinstance(v, str):
            return CONTROL_CHAR_RE.sub("", v).strip()
        return v

    @field_validator("description", mode="before")
    @classmethod
    def validate_and_sanitize_desc(cls, v: Any) -> Any:
        if not isinstance(v, str):
            v = str(v)
        cleaned = CONTROL_CHAR_RE.sub("", v).strip()
        if len(cleaned) > MAX_DESCRIPTION_LEN:
            raise ValueError(f"Alert description exceeds maximum allowed length of {MAX_DESCRIPTION_LEN} characters.")
        return cleaned

    @field_validator("symptoms", mode="before")
    @classmethod
    def validate_and_sanitize_symptoms(cls, v: Any) -> Any:
        if v is None:
            return []
        if isinstance(v, list):
            if len(v) > MAX_SYMPTOMS_COUNT:
                raise ValueError(f"Symptoms list exceeds maximum allowed count of {MAX_SYMPTOMS_COUNT} items.")
            cleaned = []
            for item in v:
                cleaned_item = CONTROL_CHAR_RE.sub("", str(item)).strip()
                if len(cleaned_item) > MAX_SYMPTOM_ITEM_LEN:
                    raise ValueError(f"Symptom item exceeds maximum allowed length of {MAX_SYMPTOM_ITEM_LEN} characters.")
                cleaned.append(cleaned_item)
            return cleaned
        return v
