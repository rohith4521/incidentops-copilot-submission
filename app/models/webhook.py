"""Alertmanager-style webhook ingestion models (Phase 6.5A).

Validates and normalizes Prometheus Alertmanager JSON payloads.
Treats all incoming fields as untrusted external telemetry.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

from app.models.security import (
    CONTROL_CHAR_RE,
)
from app.models.triage import TriageResponse


def validate_string_dict(
    d: Any,
    name: str = "dictionary",
    max_entries: int = 100,
    max_key_len: int = 256,
    max_val_len: Optional[int] = None,
) -> Dict[str, Any]:
    """Validate dictionary bounds for labels and annotations to prevent unbounded memory growth."""
    from app.config import settings

    effective_max_val_len = (
        max_val_len
        if max_val_len is not None
        else getattr(settings, "webhook_max_field_len", 8192)
    )

    if d is None:
        return {}
    if not isinstance(d, dict):
        raise ValueError(f"{name} must be a dictionary object")
    if len(d) > max_entries:
        raise ValueError(
            f"{name} entry count ({len(d)}) exceeds maximum allowed limit of {max_entries}"
        )

    cleaned: Dict[str, Any] = {}
    for k, v in d.items():
        k_str = str(k)
        if len(k_str) > max_key_len:
            raise ValueError(
                f"{name} key length ({len(k_str)}) exceeds maximum allowed ({max_key_len} characters)"
            )
        v_str = str(v) if v is not None else ""
        if len(v_str) > effective_max_val_len:
            raise ValueError(
                f"{name} value length for '{k_str[:32]}' ({len(v_str)}) exceeds maximum allowed ({effective_max_val_len} characters)"
            )
        cleaned[k_str] = v
    return cleaned


class AlertmanagerAlertItem(BaseModel):
    """An individual alert within an Alertmanager webhook payload."""
    status: str = Field(default="firing", description="Alert state: firing or resolved")
    labels: Dict[str, Any] = Field(default_factory=dict, description="Prometheus alert labels")
    annotations: Dict[str, Any] = Field(default_factory=dict, description="Prometheus alert annotations")
    startsAt: Optional[str] = Field(default=None, description="Start timestamp of alert")
    endsAt: Optional[str] = Field(default=None, description="End timestamp of alert")
    generatorURL: Optional[str] = Field(default=None, description="Prometheus query URL")
    fingerprint: Optional[str] = Field(default=None, description="Alertmanager unique alert fingerprint")

    @field_validator("status", mode="before")
    @classmethod
    def sanitize_status(cls, v: Any) -> str:
        if isinstance(v, str):
            cleaned = CONTROL_CHAR_RE.sub("", v).strip().lower()
            if len(cleaned) > 64:
                raise ValueError(f"status field length ({len(cleaned)}) exceeds limit of 64")
            return cleaned or "firing"
        return "firing"

    @field_validator("fingerprint", mode="before")
    @classmethod
    def sanitize_fingerprint(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str):
            cleaned = CONTROL_CHAR_RE.sub("", v).strip()
            if len(cleaned) > 256:
                raise ValueError(f"fingerprint length ({len(cleaned)}) exceeds limit of 256")
            return cleaned if cleaned else None
        return str(v)[:256]

    @field_validator("generatorURL", mode="before")
    @classmethod
    def sanitize_generator_url(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        v_str = str(v).strip()
        if len(v_str) > 2048:
            raise ValueError(f"generatorURL length ({len(v_str)}) exceeds limit of 2048")
        return v_str

    @field_validator("startsAt", "endsAt", mode="before")
    @classmethod
    def sanitize_timestamps(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        v_str = str(v).strip()
        if len(v_str) > 128:
            raise ValueError(f"timestamp string length ({len(v_str)}) exceeds limit of 128")
        return v_str

    @field_validator("labels", "annotations", mode="before")
    @classmethod
    def validate_item_maps(cls, v: Any, info) -> Dict[str, Any]:
        field_name = getattr(info, "field_name", "labels_or_annotations") or "labels_or_annotations"
        return validate_string_dict(v, name=field_name)


class AlertmanagerWebhookPayload(BaseModel):
    """Realistic Prometheus Alertmanager webhook payload schema."""
    version: Optional[str] = Field(default="4", description="Alertmanager notification protocol version")
    groupKey: Optional[str] = Field(default=None, description="Alertmanager group key identifier")
    truncatedAlerts: Optional[int] = Field(default=0, description="Count of truncated alerts in batch")
    status: str = Field(default="firing", description="Batch status: firing or resolved")
    receiver: Optional[str] = Field(default=None, description="Webhook receiver name")
    groupLabels: Dict[str, Any] = Field(default_factory=dict, description="Labels grouping these alerts")
    commonLabels: Dict[str, Any] = Field(default_factory=dict, description="Labels common to all alerts")
    commonAnnotations: Dict[str, Any] = Field(default_factory=dict, description="Annotations common to all alerts")
    externalURL: Optional[str] = Field(default=None, description="Alertmanager web UI URL")
    alerts: List[AlertmanagerAlertItem] = Field(default_factory=list, description="List of alert items")

    # Optional root-level fields for single alert payloads
    labels: Optional[Dict[str, Any]] = None
    annotations: Optional[Dict[str, Any]] = None
    fingerprint: Optional[str] = None
    startsAt: Optional[str] = None

    @field_validator("alerts", mode="before")
    @classmethod
    def validate_alerts_limit(cls, v: Any) -> Any:
        from app.config import settings
        max_alerts = getattr(settings, "webhook_max_alerts_count", 50)
        if isinstance(v, list) and len(v) > max_alerts:
            raise ValueError(
                f"Alert batch count ({len(v)}) exceeds maximum allowed limit of {max_alerts} alerts"
            )
        return v

    @field_validator("groupLabels", "commonLabels", "commonAnnotations", "labels", "annotations", mode="before")
    @classmethod
    def validate_batch_maps(cls, v: Any, info) -> Dict[str, Any]:
        if v is None:
            return {}
        field_name = getattr(info, "field_name", "batch_dict") or "batch_dict"
        return validate_string_dict(v, name=field_name)

    @field_validator("externalURL", mode="before")
    @classmethod
    def sanitize_external_url(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        v_str = str(v).strip()
        if len(v_str) > 2048:
            raise ValueError(f"externalURL length ({len(v_str)}) exceeds limit of 2048")
        return v_str

    @field_validator("receiver", "groupKey", mode="before")
    @classmethod
    def sanitize_text_fields(cls, v: Any, info) -> Optional[str]:
        if v is None:
            return None
        v_str = str(v).strip()
        if len(v_str) > 512:
            field_name = getattr(info, "field_name", "field") or "field"
            raise ValueError(f"{field_name} length ({len(v_str)}) exceeds limit of 512")
        return v_str


class AlertmanagerWebhookResponse(BaseModel):
    """Deterministic response returned after processing an Alertmanager webhook."""
    status: str = Field(..., description="Processing status: 'processed', 'duplicate', or 'error'")
    fingerprint: str = Field(..., description="Deterministic alert fingerprint / idempotency key")
    alert_id: str = Field(..., description="Unique alert or incident identifier")
    service: str = Field(..., description="Target service name extracted from labels")
    alertname: str = Field(..., description="Alert headline name")
    is_duplicate: bool = Field(..., description="True if webhook was an idempotent duplicate replay")
    triage_result: Optional[TriageResponse] = Field(default=None, description="Complete SRE triage response")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
