"""PHASE 7.8 — Final Backend Hardening Regression Tests.

Validates the 3 targeted release-candidate hardening changes:
1. Configurable CORS:
   - Configurable origins via settings.cors_allowed_origins
   - Standard browser-compliant origins (avoids allow_origins=['*'] + allow_credentials=True)
   - Disallowed origins rejected on preflight OPTIONS
2. Direct Memory Endpoints Protection:
   - POST /api/memory/recall requires authentication (401 without, 200 with)
   - POST /api/memory/reflect requires authentication (401 without, 200 with)
3. Trusted Proxy IP Handling:
   - X-Forwarded-For only trusted when incoming connection is from a configured trusted proxy
   - Direct client IP used when connection is from an untrusted client
   - Spoofed X-Forwarded-For cannot bypass rate limiting
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4
import pytest
from starlette.testclient import TestClient

from app.config import Settings, settings
from app.main import app
from app.models.memory import MatchStrength, RecallResultSummary
from app.services.webhook_service import idempotency_store, rate_limiter


@pytest.fixture
def client():
    """Create test client for HTTP requests."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset webhook stores between tests."""
    rate_limiter.clear()
    idempotency_store.clear()
    yield
    rate_limiter.clear()
    idempotency_store.clear()


# ===========================================================================
# 1. CORS Configuration & Preflight Tests
# ===========================================================================

def test_1_cors_allowed_origins_configuration():
    """Verify that settings parses comma-separated CORS origins and preserves local dev defaults."""
    # Default setting preserves local dev origins
    default_settings = Settings()
    origins = default_settings.cors_origins_list
    assert "http://localhost:8000" in origins
    assert "http://127.0.0.1:8000" in origins
    assert "http://localhost:3000" in origins

    # Custom setting parses cleanly
    custom = Settings(cors_allowed_origins="https://sre.internal.corp,https://ops.internal.corp")
    assert custom.cors_origins_list == [
        "https://sre.internal.corp",
        "https://ops.internal.corp",
    ]

    # Wildcard setting handled
    wildcard = Settings(cors_allowed_origins="*")
    assert wildcard.cors_origins_list == ["*"]


def test_2_cors_preflight_for_allowed_origin(client: TestClient):
    """Verify preflight OPTIONS request from an allowed origin receives standard CORS headers."""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:8000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:8000"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_3_cors_preflight_for_disallowed_origin(client: TestClient):
    """Verify preflight OPTIONS request from an untrusted origin does NOT receive allow-origin."""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://malicious-attacker-domain.evil",
            "Access-Control-Request-Method": "GET",
        },
    )
    # When origin is not allowed, Starlette CORSMiddleware omits access-control-allow-origin
    assert response.headers.get("access-control-allow-origin") is None


# ===========================================================================
# 2. Direct Memory Endpoints Protection Tests
# ===========================================================================

def test_4_memory_recall_unauthenticated_fails_with_401(client: TestClient):
    """Verify that POST /api/memory/recall rejects unauthenticated requests with HTTP 401."""
    payload = {
        "query": "Postgres deadlock on inventory_items",
        "service": "order-service",
    }
    response = client.post("/api/memory/recall", json=payload)
    assert response.status_code == 401
    assert "Authentication credentials required" in response.json()["detail"]


def test_5_memory_recall_authenticated_succeeds(client: TestClient):
    """Verify that POST /api/memory/recall accepts requests with valid SRE authentication."""
    mock_recall_result = RecallResultSummary(
        match_strength=MatchStrength.HIGH,
        is_novel=False,
        memories_found=[],
        evidence_bullets=["Recalled matching incident INC-104."],
        raw_recall_count=1,
        query_used="Postgres deadlock",
        hindsight_connected=True,
    )

    with patch("app.services.hindsight_service.hindsight_service.recall_incident_memory", new_callable=AsyncMock) as mock_recall:
        mock_recall.return_value = mock_recall_result
        payload = {
            "query": "Postgres deadlock on inventory_items",
            "service": "order-service",
        }
        response = client.post(
            "/api/memory/recall",
            headers={"X-API-Key": "sre-key-oncall"},
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["match_strength"] == "High"
        assert data["hindsight_connected"] is True


def test_6_memory_reflect_unauthenticated_fails_with_401(client: TestClient):
    """Verify that POST /api/memory/reflect rejects unauthenticated requests with HTTP 401."""
    payload = {
        "query": "Recurring failure patterns in order-service",
    }
    response = client.post("/api/memory/reflect", json=payload)
    assert response.status_code == 401
    assert "Authentication credentials required" in response.json()["detail"]


def test_7_memory_reflect_authenticated_succeeds(client: TestClient):
    """Verify that POST /api/memory/reflect accepts requests with valid SRE authentication."""
    with patch("app.services.hindsight_service.hindsight_service.reflect_insights", new_callable=AsyncMock) as mock_reflect:
        mock_reflect.return_value = "Identified recurring connection pool exhaustion."
        payload = {
            "query": "Recurring failure patterns in order-service",
        }
        response = client.post(
            "/api/memory/reflect",
            headers={"X-API-Key": "sre-key-admin"},
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["reflection"] == "Identified recurring connection pool exhaustion."
        assert "bank_id" in data


# ===========================================================================
# 3. Trusted Proxy IP Handling Tests
# ===========================================================================

def test_8_trusted_proxy_list_configuration():
    """Verify trusted_proxies configuration parsing and defaults."""
    default_settings = Settings()
    proxies = default_settings.trusted_proxies_list
    assert "127.0.0.1" in proxies
    assert "::1" in proxies
    assert "testclient" in proxies

    custom = Settings(trusted_proxies="10.0.0.1,10.0.0.2")
    assert custom.trusted_proxies_list == ["10.0.0.1", "10.0.0.2"]


def test_9_trusted_proxy_respects_forwarded_for(client: TestClient):
    """Verify that requests coming through a trusted proxy (e.g. testclient) respect X-Forwarded-For."""
    client_ip = "198.51.100.99"
    payload = {
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "fingerprint": f"fp-proxy-{uuid4().hex[:8]}",
                "labels": {"service": "checkout-service", "alertname": "ProxyTest"},
                "annotations": {"description": "Testing trusted proxy forwarding"},
            }
        ],
    }

    # Since Starlette TestClient has request.client.host == 'testclient' (a trusted proxy),
    # X-Forwarded-For is trusted
    response = client.post(
        "/api/v1/alerts/webhook",
        headers={"X-Forwarded-For": client_ip},
        json=payload,
    )
    assert response.status_code == 200

    # Verify that the rate limiter tracked the forwarded IP
    assert client_ip in rate_limiter._history


def test_10_untrusted_client_cannot_spoof_forwarded_for_to_bypass_rate_limit(client: TestClient):
    """Verify that an untrusted direct connection cannot spoof X-Forwarded-For to evade rate limits."""
    untrusted_direct_ip = "203.0.113.195"

    # Configure trusted proxies strictly to an internal gateway (excluding testclient and untrusted IP)
    with patch.object(settings, "trusted_proxies", "10.0.0.1,10.0.0.2"):
        # Configure tight rate limit: 2 requests per window
        with patch.object(rate_limiter, "_custom_max", 2), patch.object(rate_limiter, "_custom_window", 60):
            # Attacker sends request 1 with spoofed IP A
            p1 = {
                "status": "firing",
                "alerts": [
                    {
                        "status": "firing",
                        "fingerprint": f"fp-spoof-1-{uuid4().hex[:8]}",
                        "labels": {"service": "cart-service", "alertname": "SpoofTest-1"},
                        "annotations": {"description": "Spoofed attempt 1"},
                    }
                ],
            }
            # Direct client host is mocked as untrusted external IP
            with patch("starlette.datastructures.Address.host", untrusted_direct_ip):
                r1 = client.post(
                    "/api/v1/alerts/webhook",
                    headers={"X-Forwarded-For": "1.1.1.1"},
                    json=p1,
                )
                assert r1.status_code == 200

                # Attacker sends request 2 with spoofed IP B
                p2 = {
                    "status": "firing",
                    "alerts": [
                        {
                            "status": "firing",
                            "fingerprint": f"fp-spoof-2-{uuid4().hex[:8]}",
                            "labels": {"service": "cart-service", "alertname": "SpoofTest-2"},
                            "annotations": {"description": "Spoofed attempt 2"},
                        }
                    ],
                }
                r2 = client.post(
                    "/api/v1/alerts/webhook",
                    headers={"X-Forwarded-For": "2.2.2.2"},
                    json=p2,
                )
                assert r2.status_code == 200

                # Attacker sends request 3 with spoofed IP C (attempting to evade rate limit)
                p3 = {
                    "status": "firing",
                    "alerts": [
                        {
                            "status": "firing",
                            "fingerprint": f"fp-spoof-3-{uuid4().hex[:8]}",
                            "labels": {"service": "cart-service", "alertname": "SpoofTest-3"},
                            "annotations": {"description": "Spoofed attempt 3"},
                        }
                    ],
                }
                r3 = client.post(
                    "/api/v1/alerts/webhook",
                    headers={"X-Forwarded-For": "3.3.3.3"},
                    json=p3,
                )
                # Rate limit MUST trigger because the untrusted spoofed IP was ignored,
                # and all 3 requests were bound to untrusted_direct_ip!
                assert r3.status_code == 429
                assert "Process-local rate limit exceeded" in r3.json()["detail"]
