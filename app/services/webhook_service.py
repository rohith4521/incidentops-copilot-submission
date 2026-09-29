"""Webhook ingestion and idempotency service for Alertmanager alerts with SQLite persistence (Phase 7.3B).

Enforces:
1. Untrusted Input Handling: All webhook labels and annotations normalized and validated.
2. Deterministic Idempotency: Duplicate webhooks return cached triage results without duplicate side effects.
3. Durable SQLite Persistence: Deduplication records survive application restarts.
4. Concurrency Safety: Fingerprint locking prevents race conditions on concurrent duplicate requests.
5. Pipeline Reuse: Reuses existing TriageRequest, security defense, and triage_engine.
6. No Privilege Escalation: Webhooks cannot set verified_by, bypass human approval, or create trusted memories.
"""

import asyncio
from collections import deque
from datetime import datetime, timezone
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

from app.models.security import CONTROL_CHAR_RE
from app.models.triage import TriageRequest
from app.models.webhook import (
    AlertmanagerAlertItem,
    AlertmanagerWebhookPayload,
    AlertmanagerWebhookResponse,
)
from app.services.triage_engine import triage_engine

logger = logging.getLogger("incidentops.webhook")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def compute_alert_fingerprint(
    service: str,
    alertname: str,
    labels: Dict[str, Any],
    starts_at: Optional[str] = None,
    provided_fingerprint: Optional[str] = None,
) -> str:
    """Compute a deterministic, immutable fingerprint for an alert.

    If Alertmanager provided a valid non-empty fingerprint, normalizes and uses it.
    Otherwise, computes a deterministic SHA256 hex digest from the alert's immutable identity
    (service, alertname, sorted labels, and startsAt).
    """
    if provided_fingerprint and isinstance(provided_fingerprint, str):
        cleaned = CONTROL_CHAR_RE.sub("", provided_fingerprint).strip()
        if cleaned:
            return cleaned

    # Deterministic fallback: canonical representation of labels + metadata
    filtered_labels = {
        str(k).strip().lower(): str(v).strip()
        for k, v in sorted(labels.items())
        if k not in ("fingerprint",)
    }
    canonical_repr = (
        f"service={service.strip().lower()}|"
        f"alertname={alertname.strip().lower()}|"
        f"labels={json.dumps(filtered_labels, sort_keys=True)}|"
        f"starts_at={str(starts_at or '').strip()}"
    )
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()[:16]


class WebhookIdempotencyService:
    """Durable SQLite store for deterministic webhook deduplication and replay handling (Phase 7.3B)."""

    def __init__(self, db_path: Optional[str] = None):
        from app.config import settings
        if db_path:
            self.db_path = str(Path(db_path).resolve()) if db_path != ":memory:" else ":memory:"
        else:
            raw_path = getattr(settings, "webhook_db_path", "app/data/provenance_audit.db")
            p = Path(raw_path)
            self.db_path = str(p if p.is_absolute() else (PROJECT_ROOT / p).resolve())

        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()
        self._init_db()

    def _init_db(self):
        """Initialize SQLite table and index for webhook idempotency."""
        if self.db_path != ":memory:":
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with self._get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS webhook_idempotency_records (
                    fingerprint TEXT PRIMARY KEY,
                    first_seen_at TEXT NOT NULL,
                    service TEXT NOT NULL,
                    alertname TEXT NOT NULL,
                    alert_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'processed',
                    cached_response TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_webhook_fingerprint 
                ON webhook_idempotency_records(fingerprint);
            """)
            conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=20.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    async def acquire_lock(self, fingerprint: str) -> asyncio.Lock:
        """Acquire an asyncio.Lock specific to a fingerprint to serialize concurrent duplicate requests."""
        async with self._global_lock:
            if fingerprint not in self._locks:
                self._locks[fingerprint] = asyncio.Lock()
            return self._locks[fingerprint]

    def get(self, fingerprint: str) -> Optional[AlertmanagerWebhookResponse]:
        """Retrieve cached triage response from SQLite if fingerprint has been processed."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT cached_response FROM webhook_idempotency_records WHERE fingerprint = ?",
                (fingerprint.strip(),),
            )
            row = cursor.fetchone()
            if row and row["cached_response"]:
                try:
                    return AlertmanagerWebhookResponse.model_validate_json(row["cached_response"])
                except Exception as e:
                    logger.warning("Failed to deserialize cached response for fingerprint '%s': %s", fingerprint, e)
                    return None
            return None

    def record(self, fingerprint: str, response: AlertmanagerWebhookResponse) -> None:
        """Store processed webhook triage result into SQLite keyed by fingerprint."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO webhook_idempotency_records (
                    fingerprint, first_seen_at, service, alertname,
                    alert_id, status, cached_response, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    cached_response = excluded.cached_response,
                    status = excluded.status
                """,
                (
                    fingerprint.strip(),
                    now_iso,
                    response.service,
                    response.alertname,
                    response.alert_id,
                    response.status,
                    response.model_dump_json(),
                    now_iso,
                ),
            )
            conn.commit()

    def clear(self) -> None:
        """Clear cached records from SQLite (for isolated test assertions)."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM webhook_idempotency_records;")
            conn.commit()
        self._locks.clear()

    @property
    def _cache(self) -> Dict[str, AlertmanagerWebhookResponse]:
        """Backward-compatible in-memory view of cached entries."""
        res = {}
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT fingerprint, cached_response FROM webhook_idempotency_records")
            for row in cursor.fetchall():
                try:
                    res[row["fingerprint"]] = AlertmanagerWebhookResponse.model_validate_json(row["cached_response"])
                except Exception:
                    pass
        return res


# Global idempotency store singleton
idempotency_store = WebhookIdempotencyService()


class WebhookRateLimitExceeded(Exception):
    """Raised when process-local rate limit is exceeded for novel webhook ingestion."""

    def __init__(
        self,
        detail: str,
        retry_after: int,
        limit: int,
        remaining: int,
        scope: str = "process-local",
    ):
        super().__init__(detail)
        self.detail = detail
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining
        self.scope = scope


class ProcessLocalRateLimiter:
    """In-memory sliding-window rate limiter for the Alertmanager webhook boundary (Phase 7.4E).

    Compatible with the single-host architecture.
    SCOPE: Process-local. State is maintained inside this process and does not synchronize across distributed workers.
    """

    def __init__(
        self,
        max_requests: Optional[int] = None,
        window_seconds: Optional[int] = None,
        enabled: Optional[bool] = None,
    ):
        self._custom_max = max_requests
        self._custom_window = window_seconds
        self._custom_enabled = enabled

        self._history: Dict[str, deque] = {}
        self._lock = asyncio.Lock()

    @property
    def max_requests(self) -> int:
        from app.config import settings
        if self._custom_max is not None:
            return self._custom_max
        return getattr(settings, "webhook_rate_limit_requests", 60)

    @property
    def window_seconds(self) -> int:
        from app.config import settings
        if self._custom_window is not None:
            return self._custom_window
        return getattr(settings, "webhook_rate_limit_window_seconds", 60)

    @property
    def enabled(self) -> bool:
        from app.config import settings
        if self._custom_enabled is not None:
            return self._custom_enabled
        return getattr(settings, "webhook_rate_limit_enabled", True)

    @property
    def scope(self) -> str:
        return "process-local"

    async def check_and_record(self, client_ip: str) -> Tuple[bool, int, int]:
        """Check if request from client_ip is permitted within the current sliding window.

        Returns:
            (allowed: bool, remaining_requests: int, retry_after_seconds: int)
        """
        if not self.enabled:
            return True, 999999, 0

        now = time.time()
        window = float(self.window_seconds)
        cutoff = now - window

        async with self._lock:
            if client_ip not in self._history:
                self._history[client_ip] = deque()

            q = self._history[client_ip]

            # Prune timestamps outside current sliding window
            while q and q[0] <= cutoff:
                q.popleft()

            if len(q) >= self.max_requests:
                oldest_timestamp = q[0]
                retry_after = max(1, math.ceil(oldest_timestamp + window - now))
                return False, 0, retry_after

            # Record this novel request
            q.append(now)
            remaining = max(0, self.max_requests - len(q))
            return True, remaining, 0

    def clear(self) -> None:
        """Reset internal history deques (for clean test isolation)."""
        self._history.clear()


# Global rate limiter singleton
rate_limiter = ProcessLocalRateLimiter()


class WebhookIngestionService:
    """Service orchestrating validation, normalization, and triage of Alertmanager webhooks."""

    def __init__(
        self,
        engine=triage_engine,
        store=idempotency_store,
        rate_limiter: Optional[ProcessLocalRateLimiter] = None,
    ):
        self.engine = engine
        self.store = store
        self.rate_limiter = rate_limiter or globals().get("rate_limiter") or ProcessLocalRateLimiter()

    def normalize_payload(
        self,
        payload: AlertmanagerWebhookPayload,
    ) -> Tuple[AlertmanagerAlertItem, str, str, str, str, List[str], Dict[str, Any]]:
        """Extract and validate core SRE incident fields from Alertmanager payload.

        Returns: (primary_alert, service, alertname, severity, description, symptoms, context)
        Raises: ValueError if required alert data is missing.
        """
        # Determine primary alert item
        alert: Optional[AlertmanagerAlertItem] = None
        if payload.alerts and len(payload.alerts) > 0:
            alert = payload.alerts[0]
        elif payload.labels:
            alert = AlertmanagerAlertItem(
                status=payload.status,
                labels=payload.labels or {},
                annotations=payload.annotations or {},
                startsAt=payload.startsAt,
                fingerprint=payload.fingerprint,
            )

        if not alert:
            raise ValueError("Alertmanager payload contains no alerts or alert items.")

        # Combine labels (alert-level takes precedence over batch common/group labels)
        combined_labels = dict(payload.commonLabels or {})
        combined_labels.update(payload.groupLabels or {})
        combined_labels.update(alert.labels or {})

        # Combine annotations
        combined_annotations = dict(payload.commonAnnotations or {})
        combined_annotations.update(alert.annotations or {})

        # Extract target service
        service = (
            combined_labels.get("service")
            or combined_labels.get("job")
            or combined_labels.get("app")
            or combined_labels.get("microservice")
        )
        if not service or not str(service).strip():
            raise ValueError("Alertmanager alert missing target service name in labels (expected 'service', 'job', or 'app').")
        service = CONTROL_CHAR_RE.sub("", str(service)).strip()

        # Extract alertname
        alertname = (
            combined_labels.get("alertname")
            or combined_annotations.get("summary")
            or combined_labels.get("alert")
            or f"{service} Anomaly Alert"
        )
        alertname = CONTROL_CHAR_RE.sub("", str(alertname)).strip()

        # Extract severity
        raw_sev = str(combined_labels.get("severity", "HIGH")).strip().upper()
        if raw_sev in ("CRITICAL", "P1", "FATAL"):
            severity = "CRITICAL"
        elif raw_sev in ("HIGH", "P2", "WARN", "WARNING", "ERR", "ERROR"):
            severity = "HIGH"
        elif raw_sev in ("MEDIUM", "P3"):
            severity = "MEDIUM"
        elif raw_sev in ("LOW", "P4", "INFO"):
            severity = "LOW"
        else:
            severity = "HIGH"

        # Extract description
        description = (
            combined_annotations.get("description")
            or combined_annotations.get("summary")
            or combined_annotations.get("message")
            or f"Prometheus alert '{alertname}' firing on {service}."
        )
        description = CONTROL_CHAR_RE.sub("", str(description)).strip()

        # Extract symptoms
        symptoms: List[str] = []
        raw_syms = combined_annotations.get("symptoms")
        if isinstance(raw_syms, list):
            symptoms = [CONTROL_CHAR_RE.sub("", str(s)).strip() for s in raw_syms if str(s).strip()]
        elif isinstance(raw_syms, str) and raw_syms.strip():
            symptoms = [CONTROL_CHAR_RE.sub("", raw_syms).strip()]

        if not symptoms:
            summary = combined_annotations.get("summary")
            if summary and str(summary).strip() != description:
                symptoms.append(CONTROL_CHAR_RE.sub("", str(summary)).strip())
            symptoms.append(f"Alert '{alertname}' triggered condition on {service}")

        # Assemble diagnostic context
        context = {
            "labels": combined_labels,
            "annotations": combined_annotations,
            "startsAt": alert.startsAt,
            "generatorURL": alert.generatorURL,
            "receiver": payload.receiver,
        }

        return alert, service, alertname, severity, description, symptoms, context

    async def process_webhook(
        self,
        payload: AlertmanagerWebhookPayload,
        client_ip: str = "127.0.0.1",
    ) -> AlertmanagerWebhookResponse:
        """Process incoming Alertmanager webhook with deterministic idempotency and process-local rate limiting."""
        from app.services.metrics_service import metrics_service
        metrics_service.inc_webhook_requests()

        # 1. Normalize and validate payload
        alert, service, alertname, severity, description, symptoms, context = self.normalize_payload(payload)

        # 2. Compute deterministic fingerprint
        fingerprint = compute_alert_fingerprint(
            service=service,
            alertname=alertname,
            labels=alert.labels or {},
            starts_at=alert.startsAt,
            provided_fingerprint=alert.fingerprint or payload.fingerprint,
        )

        # 3. Concurrency Protection: Acquire per-fingerprint lock
        fp_lock = await self.store.acquire_lock(fingerprint)
        async with fp_lock:
            # 4. Idempotency Check: Return cached triage response if already processed
            # CRITICAL: Replays of already triaged alerts must NEVER trigger expensive triage
            # and must NEVER be blocked by rate limits.
            cached = self.store.get(fingerprint)
            if cached is not None:
                metrics_service.inc_webhook_duplicates()
                logger.info(
                    "[WEBHOOK IDEMPOTENCY] Replay detected for fingerprint '%s' (%s). "
                    "Returning cached triage result without duplicate processing.",
                    fingerprint,
                    service,
                )
                return AlertmanagerWebhookResponse(
                    status="duplicate",
                    fingerprint=fingerprint,
                    alert_id=cached.alert_id,
                    service=service,
                    alertname=alertname,
                    is_duplicate=True,
                    triage_result=cached.triage_result,
                    timestamp=cached.timestamp,
                )

            # 5. Process-Local Rate Limiting (Applied strictly to novel alerts before triage execution)
            allowed, remaining, retry_after = await self.rate_limiter.check_and_record(client_ip)
            if not allowed:
                logger.warning(
                    "[WEBHOOK RATE LIMIT] Process-local limit exceeded for client '%s'. "
                    "Limit: %d req/%ds, Retry-After: %ds (Scope: process-local)",
                    client_ip,
                    self.rate_limiter.max_requests,
                    self.rate_limiter.window_seconds,
                    retry_after,
                )
                raise WebhookRateLimitExceeded(
                    detail=(
                        f"Process-local rate limit exceeded for webhook ingestion. "
                        f"Limit: {self.rate_limiter.max_requests} novel requests per {self.rate_limiter.window_seconds}s window."
                    ),
                    retry_after=retry_after,
                    limit=self.rate_limiter.max_requests,
                    remaining=0,
                    scope=self.rate_limiter.scope,
                )

            # 6. Construct canonical TriageRequest
            # Note: All fields are validated by TriageRequest's strict security boundaries
            triage_request = TriageRequest(
                service=service,
                alert=alertname,
                description=description,
                symptoms=symptoms,
                severity=severity,
                context=context,
                enable_memory=True,
            )

            # 7. Execute production triage pipeline
            triage_result = await self.engine.triage(triage_request)

            # 8. Build and persist deterministic response in SQLite
            alert_id = getattr(triage_result, "incident_id", None) or f"ALT-{fingerprint[:8].upper()}"
            response = AlertmanagerWebhookResponse(
                status="processed",
                fingerprint=fingerprint,
                alert_id=alert_id,
                service=service,
                alertname=alertname,
                is_duplicate=False,
                triage_result=triage_result,
                timestamp=datetime.now(timezone.utc),
            )

            self.store.record(fingerprint, response)
            logger.info(
                "[WEBHOOK PROCESSED] Successfully triaged alert '%s' (%s) with fingerprint '%s'.",
                alertname,
                service,
                fingerprint,
            )
            return response


# Global webhook service singleton
webhook_service = WebhookIngestionService(rate_limiter=rate_limiter)
