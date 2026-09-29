"""Alert ingestion and automated SRE triage routes."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.models.alert import AlertPayload
from app.models.triage import TriageResult
from app.services.triage_engine import triage_engine

router = APIRouter(prefix="/alerts", tags=["Alerts & Triage"])


PRESET_SCENARIOS = [
    {
        "id": "scenario-inc-104-payment-timeout",
        "name": "🚨 Known: Payment Gateway Timeout & Thread Starvation (INC-104)",
        "type": "known",
        "expected_match": "High",
        "alert": {
            "title": "Payment API Gateway Timeout & Cascading Thread Pool Starvation",
            "service": "payment-api",
            "environment": "production",
            "severity": "CRITICAL",
            "source": "Prometheus",
            "description": "Outbound HTTPS timeout > 30s calling Stripe payment gateway API. Egress HTTP thread pool saturation across 8 replicas.",
            "symptoms": [
                "Outbound HTTPS timeout > 30s calling Stripe payment gateway API",
                "Egress HTTP thread pool saturation across 8 replicas",
                "Cascading HTTP 504 Gateway Timeout on /api/v2/checkout/charge",
                "Surge in client payment retries compounding gateway connection queue"
            ],
            "metrics": {
                "active_threads": "200/200 saturated",
                "egress_timeout_pct": "34.2%",
                "p99_latency_ms": 31200,
                "504_error_rate": "18.5%"
            },
            "cluster": "k8s-prod-us-east-1",
            "runbook_hint": "RB-PAYMENT-CIRCUIT-SHED"
        }
    },
    {
        "id": "scenario-redis-starvation",
        "name": "Known: Redis Connection Pool Starvation (Checkout)",
        "type": "known",
        "expected_match": "High",
        "alert": {
            "title": "High Error Rate & Latency Spike on Checkout Service",
            "service": "checkout-service",
            "environment": "production",
            "severity": "CRITICAL",
            "source": "Prometheus",
            "description": "HTTP 503 error rate exceeded 12% on /api/v1/checkout. Redis connection acquire timeouts spiking in logs.",
            "symptoms": [
                "p99 latency spiked to 4100ms",
                "RedisConnectionClosedException in checkout logs",
                "redis_pool_wait_duration_seconds > 2.5s",
                "HTTP 503 Service Unavailable"
            ],
            "metrics": {
                "error_rate": "13.8%",
                "p99_latency_ms": 4120,
                "redis_pool_utilization": "100%",
                "requests_per_sec": 11500
            },
            "cluster": "k8s-prod-us-east-1",
            "runbook_hint": "RB-REDIS-FAILOVER"
        }
    },
    {
        "id": "scenario-auth-oom",
        "name": "Known: Auth API JVM Heap Leak & OOMKilled Loop",
        "type": "known",
        "expected_match": "High",
        "alert": {
            "title": "Auth API Pod CrashLooping due to OOMKilled",
            "service": "auth-api",
            "environment": "production",
            "severity": "CRITICAL",
            "source": "Datadog",
            "description": "Kubernetes pods for auth-api are terminating with exit code 137 (OOMKilled). NGINX ingress reporting 502 Bad Gateway.",
            "symptoms": [
                "Pod restart count >= 4 within 15 minutes",
                "Container terminated reason: OOMKilled (Exit Code 137)",
                "Cgroup memory hit 2GiB boundary",
                "Spike in 502 Bad Gateway on /oauth/token"
            ],
            "metrics": {
                "active_pod_replicas": "2/8 healthy",
                "memory_usage_bytes": "2147483648 (100% of limit)",
                "jvm_heap_usage": "98.5%",
                "502_error_count": 890
            },
            "cluster": "k8s-prod-us-east-1",
            "runbook_hint": "RB-K8S-AUTH-HEAP-EXPAND"
        }
    },
    {
        "id": "scenario-dns-egress",
        "name": "Known: Payment Gateway Egress Timeout via Stale CoreDNS",
        "type": "known",
        "expected_match": "High",
        "alert": {
            "title": "Payment Processor Egress Connection Timeouts",
            "service": "payment-gateway",
            "environment": "production",
            "severity": "HIGH",
            "source": "PagerDuty",
            "description": "Outbound HTTP requests to third-party payment provider timing out after 30s. CoreDNS metrics indicate SERVFAIL.",
            "symptoms": [
                "Egress connection timeout to api.stripe.com",
                "CoreDNS cache lookup failure",
                "Customer payment failures at 22%",
                "HTTP client socket timeout after 30000ms"
            ],
            "metrics": {
                "failed_payment_pct": "24.5%",
                "egress_timeout_count": 420,
                "dns_lookup_latency_ms": 30500
            },
            "cluster": "k8s-prod-us-east-1",
            "runbook_hint": "RB-COREDNS-FLUSH-EGRESS"
        }
    },
    {
        "id": "scenario-novel-kafka-poison-pill",
        "name": "Novel: Kafka Deserialization Poison Pill & Partition Skew",
        "type": "novel",
        "expected_match": "None",
        "alert": {
            "title": "Unprecedented Kafka Consumer Lag & Deserialization Trap",
            "service": "event-stream-consumer",
            "environment": "production",
            "severity": "CRITICAL",
            "source": "Prometheus",
            "description": "Consumer group 'order-events-processor' partition 7 lag grew from 10 to 450,000 messages. Worker threads stuck in infinite retry loop on unparseable Avro byte payload.",
            "symptoms": [
                "Consumer lag surging past 400k messages on single partition",
                "Unhandled RecordDeserializationException in consumer logs",
                "No dead-letter queue configured for corrupt Avro magic byte 0x7F",
                "Thread dump shows 12 consumer threads blocked on offset commit"
            ],
            "metrics": {
                "consumer_lag": 451200,
                "partition_skew_ratio": "99:1",
                "processing_rate_eps": 0,
                "deserialization_error_rate": "100% on partition 7"
            },
            "cluster": "k8s-prod-us-west-2",
            "runbook_hint": None
        }
    }
]


@router.get("/presets")
async def get_preset_alerts():
    """Return pre-configured operational alert scenarios (both known and novel)."""
    return PRESET_SCENARIOS


@router.post("/triage", response_model=TriageResult)
async def triage_alert(
    alert: AlertPayload,
    model: Optional[str] = Query(None, description="Optional Groq model override (e.g. qwen-2.5-32b)"),
):
    """Ingest an operational alert and perform end-to-end memory-augmented SRE triage."""
    try:
        result = await triage_engine.execute_triage(alert=alert, override_model=model)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Triage execution failed: {str(e)}",
        )
