"""Tests for FastAPI API routes and integration flows."""

import pytest
from app.models.alert import AlertPayload


def test_health_endpoint(client):
    """Verify GET /api/health returns system and Hindsight status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "hindsight" in data
    assert "groq" in data
    assert "invariants_enforced" in data


def test_alerts_presets_endpoint(client):
    """Verify GET /api/alerts/presets returns operational scenarios."""
    response = client.get("/api/alerts/presets")
    assert response.status_code == 200
    presets = response.json()
    assert len(presets) >= 4
    scenario_types = [p["type"] for p in presets]
    assert "known" in scenario_types
    assert "novel" in scenario_types


def test_alert_triage_flow_and_invariant_4_enforcement(client):
    """Verify alert triage -> runbook recommendation -> approval gate -> simulation."""
    alert_payload = {
        "title": "Database Lock Contention",
        "service": "order-service",
        "environment": "production",
        "severity": "HIGH",
        "source": "Prometheus",
        "description": "Postgres deadlock detected on inventory tables.",
        "symptoms": ["Deadlock detected: Process waiting for ShareLock"],
        "metrics": {"deadlock_rate": "18/min"},
    }

    # Step 1: Execute Triage
    triage_resp = client.post("/api/alerts/triage", json=alert_payload)
    assert triage_resp.status_code == 200
    triage_data = triage_resp.json()
    assert "incident_id" in triage_data
    assert "match_strength" in triage_data
    assert triage_data["match_strength"] in ["High", "Moderate", "None"]

    rb = triage_data.get("recommended_runbook")
    assert rb is not None
    rb_id = rb["id"]
    assert rb["status"] == "PENDING_APPROVAL"

    # Step 2: Attempt simulation before approval -> STRICTLY BLOCKED (Invariant 4)
    sim_resp_blocked = client.post(
        f"/api/runbooks/{rb_id}/simulate",
        json={"executor": "unauthorized-operator"},
    )
    assert sim_resp_blocked.status_code == 400
    assert "requires human approval before simulation" in sim_resp_blocked.json()["detail"]

    # Step 3: Approve runbook (Authenticated Human SRE)
    approve_resp = client.post(
        f"/api/runbooks/{rb_id}/approve",
        headers={"X-API-Key": "sre-key-oncall"},
        json={"notes": "Approved for emergency mitigation"},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "APPROVED"
    assert approve_resp.json()["approver"] == "oncall-sre"

    # Step 4: Simulate runbook -> SUCCEEDS
    sim_resp_ok = client.post(
        f"/api/runbooks/{rb_id}/simulate",
        json={"executor": "lead-sre@company.internal"},
    )
    assert sim_resp_ok.status_code == 200
    assert sim_resp_ok.json()["success"] is True
    assert len(sim_resp_ok.json()["logs"]) > 0


def test_postmortem_draft_endpoint(client):
    """Verify drafting a post-mortem from a triage result."""
    alert_payload = {
        "title": "Auth API Outage",
        "service": "auth-api",
        "description": "Auth service down",
        "symptoms": ["OOMKilled"],
    }
    triage_resp = client.post("/api/alerts/triage", json=alert_payload)
    triage_data = triage_resp.json()

    draft_resp = client.post(
        "/api/postmortems/draft",
        json={
            "triage_result": triage_data,
            "incident_title": "Resolved Auth API Outage",
            "confirmed_resolution": "Patched heap limit to 4GiB",
        },
    )
    assert draft_resp.status_code == 200
    draft = draft_resp.json()
    assert draft["service"] == "auth-api"
    assert "timeline" in draft
    assert "resolution_steps" in draft


def test_dashboard_ui_served(client):
    """Verify dashboard index.html is served at root."""
    response = client.get("/")
    assert response.status_code == 200
    assert "IncidentOps Copilot" in response.text
