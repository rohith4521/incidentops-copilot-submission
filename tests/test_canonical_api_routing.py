"""PHASE 7.2 — Canonical API Routing Cleanup Tests.

Validates:
1. Canonical POST /api/v1/triage works and returns standard TriageResponse.
2. Canonical GET /api/v1/health works and returns comprehensive health & dependencies.
3. Legacy compatibility aliases (POST /api/triage, GET /api/health, POST /api/alerts/triage) delegate correctly without logic duplication.
4. Frontend source code (app.js, index.html) contains no obsolete primary API calls (/api/health or unversioned /api/triage).
"""

from pathlib import Path
import re
import pytest
from starlette.testclient import TestClient

from app.main import app

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def client():
    """Create Starlette test client."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Test 1: Canonical /api/v1/triage works
# ---------------------------------------------------------------------------

def test_1_canonical_v1_triage_works(client: TestClient):
    """Verify that canonical POST /api/v1/triage processes incident alerts and returns valid TriageResponse."""
    payload = {
        "service": "checkout-service",
        "title": "Payment gateway timeout on checkout",
        "severity": "HIGH",
        "symptoms": [
            "HTTP 504 Gateway Timeout",
            "Stripe API latency spiked > 3000ms",
        ],
        "enable_memory": False,  # Stateless test for fast deterministic validation
    }
    response = client.post("/api/v1/triage", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()

    assert "incident_summary" in data
    assert "likely_root_cause" in data
    assert "novelty" in data
    assert "requires_human_approval" in data
    assert data["requires_human_approval"] is True


# ---------------------------------------------------------------------------
# Test 2: Canonical /api/v1/health works
# ---------------------------------------------------------------------------

def test_2_canonical_v1_health_works(client: TestClient):
    """Verify that canonical GET /api/v1/health reports system status and dependencies."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()

    assert "status" in data
    assert data["status"] in ("healthy", "degraded")
    assert "timestamp" in data
    assert "dependencies" in data

    deps = data["dependencies"]
    assert "api" in deps
    assert "hindsight" in deps
    assert "llm_provider" in deps

    # Backward-compatible convenience fields for UI and legacy callers
    assert "bank_id" in data
    assert "hindsight" in data
    assert "groq" in data
    assert "invariants_enforced" in data


# ---------------------------------------------------------------------------
# Test 3: Existing compatibility aliases delegate correctly
# ---------------------------------------------------------------------------

def test_3_legacy_triage_alias_delegates_to_v1(client: TestClient):
    """Verify that legacy POST /api/triage alias remains fully functional via delegation."""
    payload = {
        "service": "order-service",
        "title": "Database connection pool exhaustion",
        "severity": "CRITICAL",
        "symptoms": ["Connection pool empty", "Active connections: 100/100"],
        "enable_memory": False,
    }
    # Call legacy unversioned endpoint
    legacy_resp = client.post("/api/triage", json=payload)
    assert legacy_resp.status_code == 200, f"Legacy /api/triage failed: {legacy_resp.text}"
    legacy_data = legacy_resp.json()

    # Call canonical versioned endpoint with identical payload
    canonical_resp = client.post("/api/v1/triage", json=payload)
    assert canonical_resp.status_code == 200
    canonical_data = canonical_resp.json()

    # Structural delegation check
    assert legacy_data["requires_human_approval"] == canonical_data["requires_human_approval"]
    assert legacy_data["novelty"] == canonical_data["novelty"]
    assert "likely_root_cause" in legacy_data
    assert "incident_summary" in legacy_data


def test_4_legacy_health_alias_delegates_to_v1(client: TestClient):
    """Verify that legacy GET /api/health alias delegates directly to canonical /api/v1/health."""
    legacy_resp = client.get("/api/health")
    assert legacy_resp.status_code == 200
    legacy_data = legacy_resp.json()

    canonical_resp = client.get("/api/v1/health")
    assert canonical_resp.status_code == 200
    canonical_data = canonical_resp.json()

    # Ensure identical status and dependency reporting
    assert legacy_data["status"] == canonical_data["status"]
    assert legacy_data["bank_id"] == canonical_data["bank_id"]
    assert legacy_data["dependencies"]["api"]["version"] == canonical_data["dependencies"]["api"]["version"]
    assert legacy_data["invariants_enforced"] == canonical_data["invariants_enforced"]


def test_5_legacy_alerts_triage_alias_remains_functional(client: TestClient):
    """Verify that legacy POST /api/alerts/triage endpoint remains functional for AlertPayload callers."""
    payload = {
        "title": "Postgres Lock Contention",
        "service": "order-service",
        "environment": "production",
        "severity": "HIGH",
        "source": "Prometheus",
        "description": "Postgres deadlock detected on inventory tables.",
        "symptoms": ["Deadlock detected: Process waiting for ShareLock"],
        "metrics": {"deadlock_rate": "12/min"},
    }
    response = client.post("/api/alerts/triage", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "incident_id" in data
    assert "match_strength" in data
    assert "recommended_runbook" in data


# ---------------------------------------------------------------------------
# Test 6: Frontend source contains no obsolete primary API calls
# ---------------------------------------------------------------------------

def test_6_frontend_source_contains_no_obsolete_api_calls():
    """Verify that frontend JavaScript and HTML files do NOT contain obsolete unversioned API calls."""
    js_path = PROJECT_ROOT / "app" / "static" / "js" / "app.js"
    html_path = PROJECT_ROOT / "app" / "static" / "index.html"

    assert js_path.exists(), "app.js must exist"
    assert html_path.exists(), "index.html must exist"

    js_content = js_path.read_text(encoding="utf-8")
    html_content = html_path.read_text(encoding="utf-8")

    # 1. No obsolete /api/health calls
    assert 'fetch("/api/health")' not in js_content, "app.js must not call /api/health"
    assert "fetch('/api/health')" not in js_content, "app.js must not call /api/health"
    assert "/api/health" not in html_content, "index.html must not reference obsolete /api/health"

    # 2. No unversioned /api/triage calls (must be /api/v1/triage)
    # Check that any fetch call to triage uses /api/v1/triage
    unversioned_fetch_triage = re.findall(r'fetch\([\'"]/api/triage[\'"]', js_content)
    assert len(unversioned_fetch_triage) == 0, f"Found unversioned triage fetch in app.js: {unversioned_fetch_triage}"

    # Verify canonical /api/v1/triage is called in app.js
    assert 'fetch("/api/v1/triage"' in js_content or "fetch('/api/v1/triage'" in js_content, (
        "app.js must use canonical fetch('/api/v1/triage')"
    )

    # Verify canonical /api/v1/health is called in app.js
    assert 'fetch("/api/v1/health")' in js_content or "fetch('/api/v1/health')" in js_content, (
        "app.js must use canonical fetch('/api/v1/health')"
    )

    # 3. Check button label in index.html references canonical /api/v1/triage
    assert "(/api/triage)" not in html_content, "index.html button text must not reference unversioned /api/triage"
    assert "(/api/v1/triage)" in html_content, "index.html button text must reference canonical /api/v1/triage"
