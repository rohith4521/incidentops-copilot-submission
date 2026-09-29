"""Backend Observability, Correlation ID Tracking & Structured Logging (Phase 6.8A).

Provides:
1. Correlation/Request ID middleware with header propagation (X-Correlation-ID).
2. ContextVar tracking for request correlation across async task boundaries.
3. Secret-scrubbing structured JSON log formatting.
4. Defense against logging API keys, JWT secrets, credentials, or raw injection payloads.
"""

from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import re
from typing import Any, Dict
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.services.metrics_service import metrics_service

# Context variable storing correlation ID for the active async request context
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")

# Regex patterns for credential scrubbing
SECRET_PATTERNS = [
    re.compile(r"gsk_[a-zA-Z0-9_\-]{20,}", re.IGNORECASE),
    re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
    re.compile(r"ey[a-zA-Z0-9_\-]{15,}\.[a-zA-Z0-9_\-]{15,}\.[a-zA-Z0-9_\-]{15,}", re.IGNORECASE),
    re.compile(r"(?:api[_\-]?key|secret|password|token)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{8,}['\"]?", re.IGNORECASE),
]

SENSITIVE_FIELD_NAMES = {
    "api_key",
    "apikey",
    "groq_api_key",
    "hindsight_api_key",
    "jwt_secret",
    "auth_jwt_secret",
    "secret",
    "secrets",
    "password",
    "passwords",
    "token",
    "tokens",
    "authorization",
    "auth",
    "credentials",
    "credential",
}


def get_correlation_id() -> str:
    """Return the current async context correlation ID, or empty string if unset."""
    return correlation_id_ctx.get("")


def scrub_secrets_from_text(text: str) -> str:
    """Mask credential strings, API keys, and bearer tokens from text."""
    if not text:
        return ""
    sanitized = str(text)
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized


def sanitize_log_data(data: Any, max_string_len: int = 250) -> Any:
    """Recursively scrub secrets and sensitive fields from dictionary or list payloads."""
    if isinstance(data, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in data.items():
            if str(k).lower() in SENSITIVE_FIELD_NAMES:
                cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = sanitize_log_data(v, max_string_len)
        return cleaned
    elif isinstance(data, list):
        return [sanitize_log_data(item, max_string_len) for item in data]
    elif isinstance(data, str):
        scrubbed = scrub_secrets_from_text(data)
        if len(scrubbed) > max_string_len:
            return scrubbed[:max_string_len] + "... [TRUNCATED]"
        return scrubbed
    elif isinstance(data, (int, float, bool)) or data is None:
        return data
    else:
        return scrub_secrets_from_text(str(data))


class StructuredJsonFormatter(logging.Formatter):
    """Custom logging formatter that outputs JSON lines with correlation ID and secret scrubbing."""

    def format(self, record: logging.LogRecord) -> str:
        corr_id = getattr(record, "correlation_id", None) or get_correlation_id() or None
        event_name = getattr(record, "event", None)

        raw_message = record.getMessage()
        safe_message = scrub_secrets_from_text(raw_message)

        log_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": safe_message,
            "correlation_id": corr_id,
        }

        if event_name:
            log_payload["event"] = event_name

        # Extract extra structured attributes passed to logger
        extra_attrs = getattr(record, "extra_data", None)
        if isinstance(extra_attrs, dict):
            log_payload["data"] = sanitize_log_data(extra_attrs)

        return json.dumps(log_payload)


def log_backend_event(
    logger_instance: logging.Logger,
    event: str,
    message: str,
    level: int = logging.INFO,
    **extra_data: Any,
) -> None:
    """Convenience helper to emit a structured backend event log with scrubbed payload."""
    corr_id = get_correlation_id()
    safe_extra = sanitize_log_data(extra_data)
    safe_msg = scrub_secrets_from_text(message)

    extra_dict = {
        "event": event,
        "correlation_id": corr_id or None,
        "extra_data": safe_extra,
    }
    logger_instance.log(level, safe_msg, extra=extra_dict)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Starlette middleware establishing request correlation ID and tracking metrics."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Check incoming headers for existing correlation ID
        incoming_id = (
            request.headers.get("x-correlation-id")
            or request.headers.get("x-request-id")
            or request.headers.get("correlation-id")
        )

        if incoming_id and incoming_id.strip():
            corr_id = incoming_id.strip()
        else:
            corr_id = f"corr-{uuid4().hex[:16]}"

        request.state.correlation_id = corr_id
        token = correlation_id_ctx.set(corr_id)

        # Track total requests metric
        metrics_service.inc_total_requests()

        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = corr_id
            response.headers["X-Request-ID"] = corr_id
            return response
        finally:
            correlation_id_ctx.reset(token)
