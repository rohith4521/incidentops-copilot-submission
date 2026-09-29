"""Alertmanager webhook ingestion API route (Phase 6.5A & Phase 7.4E).

Provides:
POST /api/v1/alerts/webhook
Accepts Prometheus Alertmanager-style JSON notifications.
Enforces:
1. Bounded request body size (Content-Length and streamed byte cap -> HTTP 413).
2. Malformed JSON safe rejection (HTTP 400).
3. Schema and field-length bounds validation (HTTP 422).
4. Configurable process-local sliding-window rate limiting (HTTP 429).
5. Persistent idempotency preservation (replays return cached 200 without triage or rate limit block).
"""

import json
import logging
from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import ValidationError

from app.config import settings
from app.models.webhook import (
    AlertmanagerWebhookPayload,
    AlertmanagerWebhookResponse,
)
from app.services.webhook_service import (
    WebhookRateLimitExceeded,
    webhook_service,
)

logger = logging.getLogger("incidentops.api.webhook")

# Router mounted at /v1/alerts under /api (resulting in /api/v1/alerts/webhook)
router = APIRouter(prefix="/v1/alerts", tags=["Alertmanager Webhook Ingestion"])


@router.post(
    "/webhook",
    response_model=AlertmanagerWebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest Alertmanager webhook alert",
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": AlertmanagerWebhookPayload.model_json_schema()
                }
            },
            "required": True,
        }
    },
)
async def ingest_alertmanager_webhook(
    request: Request,
    response: Response,
) -> AlertmanagerWebhookResponse:
    """Ingest, validate, and triage a Prometheus Alertmanager webhook alert.

    Guarantees:
    - Bounded Request: Maximum payload size enforced (HTTP 413).
    - Malformed Protection: Unparseable JSON rejected safely (HTTP 400).
    - Bounds Enforcement: Maximum alert count and label/annotation field lengths capped (HTTP 422).
    - Process-local Rate Limiting: Novel alert storms throttled (HTTP 429).
    - Persistent Idempotency: Duplicate replays safely return cached triage results (HTTP 200).
    - Untrusted Data Boundary: Prompt injection defused; cannot forge verified_by or trusted memory.
    """
    max_bytes = getattr(settings, "webhook_max_body_bytes", 256 * 1024)

    # 1. Content-Length header pre-flight check
    content_length_header = request.headers.get("content-length")
    if content_length_header:
        try:
            cl = int(content_length_header)
            if cl > max_bytes:
                logger.warning(
                    "Alertmanager webhook rejected: Content-Length %d exceeds max %d bytes",
                    cl,
                    max_bytes,
                )
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Webhook payload size ({cl} bytes) exceeds maximum limit of {max_bytes} bytes",
                )
        except ValueError:
            pass

    # 2. Read body in chunks with byte-level limit to prevent unbounded memory growth
    chunks = []
    total_bytes = 0
    async for chunk in request.stream():
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            logger.warning(
                "Alertmanager webhook rejected: Body stream exceeds max %d bytes",
                max_bytes,
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Webhook payload size exceeds maximum limit of {max_bytes} bytes",
            )
        chunks.append(chunk)

    body_bytes = b"".join(chunks)

    # 3. Parse JSON safely, catching malformed syntax
    try:
        raw_json = json.loads(body_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as jde:
        logger.warning("Malformed JSON in webhook request body: %s", jde)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed JSON payload in request body: {str(jde)}",
        )

    # 4. Validate schema with strict bounds
    try:
        payload = AlertmanagerWebhookPayload.model_validate(raw_json)
    except ValidationError as ve:
        logger.warning("Alertmanager webhook schema validation error: %s", ve)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=json.loads(ve.json()),
        )

    # 5. Extract client identifier for process-local rate limiting
    direct_ip = request.client.host if (request.client and request.client.host) else "127.0.0.1"
    forwarded_for = request.headers.get("x-forwarded-for")

    # Only trust X-Forwarded-For if incoming connection is from a configured trusted proxy
    trusted_proxies = settings.trusted_proxies_list
    if forwarded_for and (direct_ip in trusted_proxies or "*" in trusted_proxies):
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = direct_ip

    # Expose process-local rate limit scope in response headers
    response.headers["X-RateLimit-Scope"] = "process-local"

    # 6. Process webhook with idempotency & rate limiting
    try:
        result = await webhook_service.process_webhook(payload, client_ip=client_ip)
        return result
    except WebhookRateLimitExceeded as rle:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=rle.detail,
            headers={
                "Retry-After": str(rle.retry_after),
                "X-RateLimit-Limit": str(rle.limit),
                "X-RateLimit-Remaining": str(rle.remaining),
                "X-RateLimit-Scope": rle.scope,
            },
        )
    except ValueError as ve:
        logger.warning("Alertmanager webhook validation error: %s", ve)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Alertmanager webhook processing failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook ingestion failed: {str(e)}",
        )
