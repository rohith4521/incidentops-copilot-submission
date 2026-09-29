"""Pytest configuration and shared fixtures for IncidentOps Copilot."""

import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings
from app.main import app
from app.models.alert import AlertPayload, AlertSeverity, AlertSource


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def sample_known_alert():
    """Sample alert correlating with historical Redis connection exhaustion."""
    return AlertPayload(
        id="ALT-TEST-REDIS-01",
        title="High Error Rate & Latency Spike on Checkout Service",
        service="checkout-service",
        environment="production",
        severity=AlertSeverity.CRITICAL,
        source=AlertSource.PROMETHEUS,
        description="HTTP 503 error rate exceeded 12% on /api/v1/checkout. Redis connection acquire timeouts spiking.",
        symptoms=[
            "p99 latency spiked to 4100ms",
            "RedisConnectionClosedException in checkout logs",
            "redis_pool_wait_duration_seconds > 2.5s",
        ],
        metrics={
            "error_rate": "13.8%",
            "p99_latency_ms": 4120,
            "redis_pool_utilization": "100%",
        },
        cluster="k8s-prod-us-east-1",
    )


@pytest.fixture
def sample_novel_alert():
    """Sample novel alert with zero historical precedent."""
    return AlertPayload(
        id="ALT-TEST-NOVEL-01",
        title="Unprecedented Kafka Consumer Lag & Deserialization Trap",
        service="event-stream-consumer",
        environment="production",
        severity=AlertSeverity.CRITICAL,
        source=AlertSource.PROMETHEUS,
        description="Consumer group partition 7 lag grew to 450,000 messages. Worker threads stuck in infinite retry loop.",
        symptoms=[
            "Consumer lag surging past 400k messages on single partition",
            "Unhandled RecordDeserializationException in consumer logs",
            "Corrupt Avro magic byte 0x7F",
        ],
        metrics={
            "consumer_lag": 451200,
            "partition_skew_ratio": "99:1",
        },
        cluster="k8s-prod-us-west-2",
    )


@pytest.fixture
def inc_104_recall_summary():
    """Mock recall summary corresponding to historical incident INC-104 for offline test isolation."""
    from app.models.memory import IncidentMemoryItem, MatchStrength, RecallResultSummary

    item = IncidentMemoryItem(
        id="mem-inc-104",
        incident_id="INC-104",
        service="payment-api",
        severity="CRITICAL",
        alert_signature="PaymentGatewayEgressTimeoutBreached",
        title="Payment API Gateway Timeout & Cascading Thread Pool Starvation",
        symptoms=[
            "Outbound HTTPS timeout > 30s calling Stripe payment gateway API",
            "Egress HTTP thread pool saturation across 8 replicas",
            "Cascading HTTP 504 Gateway Timeout on /api/v2/checkout/charge",
            "Surge in client payment retries compounding gateway connection queue",
        ],
        root_cause=(
            "Upstream third-party payment processor experienced routing degradation on edge proxies. "
            "The payment-api HTTP client lacked aggressive socket connect timeouts (defaulted to 60s) "
            "and lacked an active circuit breaker, allowing thousands of concurrent charge requests to block worker threads."
        ),
        failed_mitigations=[
            "Restarting payment-api pods alone caused immediate re-saturation as client retry storms hit pods during initialization.",
            "Increasing payment-api replica count from 8 to 24 aggravated upstream firewall connection limits.",
        ],
        verified_runbook="RB-PAYMENT-CIRCUIT-SHED",
        runbook_used="RB-PAYMENT-CIRCUIT-SHED",
        postmortem_summary=(
            "Cascading payment-api outage caused by upstream gateway latency and missing circuit breaker. "
            "Resolved by applying RB-PAYMENT-CIRCUIT-SHED to trip the circuit breaker, route traffic to asynchronous payment queue, "
            "and adjust HTTP client connect timeout to 3.5s."
        ),
        resolution="Applied RB-PAYMENT-CIRCUIT-SHED: tripped circuit breaker to shed load, redirected payments to durable async intake buffer, and patched socket timeout to 3.5s.",
        tags=["payment-api", "api-failure", "circuit-breaker", "RB-PAYMENT-CIRCUIT-SHED", "INC-104"],
        memory_status=MatchStrength.HIGH and __import__("app.models.memory", fromlist=["MemoryStatus"]).MemoryStatus.VERIFIED,
        source_type=__import__("app.models.memory", fromlist=["MemorySourceType"]).MemorySourceType.HUMAN_VERIFIED,
        verified_by="sre-core-team",
    )

    return RecallResultSummary(
        match_strength=MatchStrength.HIGH,
        is_novel=False,
        memories_found=[item],
        candidates_retrieved=[item],
        relevance_verdict="ACCEPTED",
        evidence_bullets=[
            "High correlation: Both target service 'payment-api' and observed symptoms have documented prior post-mortems.",
            "Verifiable failure signature match: 'outbound' aligns with historical incident INC-104",
            "Recalled prior incident: INC-104 (Payment API Gateway Timeout & Cascading Thread Pool Starvation)",
            "Historically proven runbook referenced: RB-PAYMENT-CIRCUIT-SHED",
        ],
        raw_recall_count=1,
        query_used="Service: payment-api. Alert: PaymentGatewayEgressTimeoutBreached.",
        hindsight_connected=True,
    )

