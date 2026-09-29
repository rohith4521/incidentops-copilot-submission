"""Tests for Hindsight memory service, match strength evaluation, and resilience."""

import pytest
from app.models.alert import AlertPayload, AlertSeverity
from app.models.memory import IncidentMemoryItem, MatchStrength
from app.services.hindsight_service import HindsightMemoryService


def test_evaluate_match_strength_exact_match(sample_known_alert):
    """Verify that exact service match + symptom overlap produces High MatchStrength."""
    service = HindsightMemoryService()
    items = [
        IncidentMemoryItem(
            id="mem-1",
            incident_id="INC-402",
            service="checkout-service",
            title="Redis Connection Pool Starvation",
            root_cause="Connection pool exhaustion",
            resolution="Sentinel failover",
            runbook_used="RB-REDIS-FAILOVER",
            raw_text="checkout-service RedisConnectionClosedException under high traffic. RB-REDIS-FAILOVER resolved it.",
        )
    ]

    strength, bullets = service._evaluate_match_strength(sample_known_alert, items)
    assert strength == MatchStrength.HIGH
    assert any("High correlation" in b for b in bullets)
    assert any("INC-402" in b for b in bullets)


def test_evaluate_match_strength_empty_novel(sample_novel_alert):
    """Verify that zero items produces None MatchStrength (Novelty)."""
    service = HindsightMemoryService()
    strength, bullets = service._evaluate_match_strength(sample_novel_alert, [])
    assert strength == MatchStrength.NONE
    assert any("No historical incidents found" in b for b in bullets)


def test_evaluate_match_strength_partial_moderate():
    """Verify that partial match produces Moderate MatchStrength."""
    service = HindsightMemoryService()
    alert = AlertPayload(
        title="High Memory Usage in Cart Service",
        service="cart-service",
        description="Memory usage climbing",
        symptoms=["Memory leak in token cache"],
    )
    # Item matches symptom but different service
    items = [
        IncidentMemoryItem(
            id="mem-2",
            incident_id="INC-519",
            service="auth-api",
            title="Auth API Heap Leak",
            raw_text="Memory leak in token cache causing OOMKilled",
        )
    ]
    strength, bullets = service._evaluate_match_strength(alert, items)
    assert strength == MatchStrength.MODERATE
    assert any("Moderate correlation" in b for b in bullets)


@pytest.mark.asyncio
async def test_hindsight_direct_connectivity_check():
    """Verify check_health directly probes the configured Hindsight API endpoint."""
    service = HindsightMemoryService(base_url="https://api.hindsight.vectorize.io")
    health = await service.check_health()
    assert "status" in health
    assert "endpoint" in health
    # Endpoint should return 'connected' (if public), 'unauthorized' (if key needed), or 'unreachable'
    assert health["status"] in ["connected", "unauthorized", "unreachable"]
