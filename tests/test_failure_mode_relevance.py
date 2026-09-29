"""PHASE 5.2 — Tests for Failure-Mode-Aware Relevance Scoring and Decoy Rejection.

Covers the 10 required test cases:
1. Existing INC-104 known alert -> accepted (HIGH match).
2. INC-104 paraphrase -> accepted (HIGH match).
3. INC-104 TLS/different-failure-mode decoy -> rejected (NONE match, domain conflict).
4. PostgreSQL disk exhaustion vs deadlock -> rejected (storage_disk vs db_locking).
5. Redis Sentinel partition vs Redis eviction -> rejected (consensus_quorum vs cache_memory_eviction).
6. Kafka mTLS handshake vs Avro poison pill -> rejected (security_tls vs messaging_poison_pill).
7. Regex CPU lockup vs Redis pool exhaustion -> rejected (algorithmic_cpu vs connection_pool).
8. Novel incident -> no accepted historical precedent (novelty=True, historical_matches=[]).
9. Service-only similarity -> never HIGH (invariant enforcement).
10. Existing stateless mode still bypasses memory (memory_used=False).
"""

from unittest.mock import AsyncMock, patch
import pytest

from app.models.alert import AlertPayload, AlertSeverity, AlertSource
from app.models.memory import IncidentMemoryItem, MatchStrength, RecallResultSummary
from app.models.triage import TriageRequest
from app.services.hindsight_service import HindsightMemoryService, hindsight_service
from app.services.relevance_scorer import (
    evaluate_batch_relevance,
    score_candidate_relevance,
)
from app.services.triage_engine import triage_engine


# ---------------------------------------------------------------------------
# Seed Incident Memory Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mem_inc_104():
    return IncidentMemoryItem(
        id="mem-104",
        incident_id="INC-104",
        service="payment-api",
        severity="CRITICAL",
        alert_signature="PaymentGatewayEgressTimeoutBreached",
        title="Payment API Gateway Timeout & Cascading Thread Pool Starvation",
        symptoms=[
            "Outbound HTTPS timeout > 30s calling Stripe payment gateway API",
            "Egress HTTP thread pool saturation across 8 replicas",
            "Cascading HTTP 504 Gateway Timeout on /api/v2/checkout/charge",
        ],
        root_cause="Upstream payment processor latency caused HTTP client socket connect timeouts to exhaust thread pool.",
        failed_mitigations=["Restarting payment-api pods alone caused immediate re-saturation."],
        verified_runbook="RB-PAYMENT-CIRCUIT-SHED",
        runbook_used="RB-PAYMENT-CIRCUIT-SHED",
        tags=["payment-api", "api-failure", "circuit-breaker", "stripe", "INC-104"],
        raw_text="Payment API gateway timeout and thread pool starvation under Stripe API latency.",
    )


@pytest.fixture
def mem_inc_108():
    return IncidentMemoryItem(
        id="mem-108",
        incident_id="INC-108",
        service="order-db-primary",
        severity="CRITICAL",
        alert_signature="PostgresDeadlockRateSpikeAndLockQueueSaturation",
        title="Primary Database Deadlock Storm & Transaction Isolation Contention",
        symptoms=[
            "PostgreSQL active lock wait queue exceeded 180 connections",
            "SQLSTATE 40P01 (deadlock detected) on concurrent inventory row updates",
            "Spike in backend transactions rolling back with transaction abortion",
        ],
        root_cause="Two concurrent transactional workflows acquired row-level ExclusiveLocks on inventory_items in opposing order.",
        failed_mitigations=["Increasing PostgreSQL max_connections from 300 to 800."],
        verified_runbook="RB-PG-KILL-LOCKS-ORDER-SORT",
        runbook_used="RB-PG-KILL-LOCKS-ORDER-SORT",
        tags=["order-db-primary", "database", "postgres", "deadlock", "locks", "INC-108"],
        raw_text="Primary database deadlock storm and lock contention on inventory updates.",
    )


@pytest.fixture
def mem_inc_203():
    return IncidentMemoryItem(
        id="mem-203",
        incident_id="INC-203",
        service="auth-cache-service",
        severity="HIGH",
        alert_signature="RedisEvictionPolicyFailureAndJWTCacheOOM",
        title="Auth Cache Memory Exhaustion & JWT Validation Latency Surge",
        symptoms=[
            "Redis memory usage reached 100% maxmemory ceiling with OOM command errors",
            "Auth token verification latency spiked from 4ms to 1200ms",
            "Downstream services receiving HTTP 500 on JWT public key cache lookup",
        ],
        root_cause="Redis cluster key eviction policy was configured to noeviction instead of volatile-lru, saturating cache memory.",
        failed_mitigations=["Flushing entire cache with FLUSHDB caused a catastrophic cache stampede."],
        verified_runbook="RB-REDIS-EVICTION-TUNE-SCALE",
        runbook_used="RB-REDIS-EVICTION-TUNE-SCALE",
        tags=["auth-cache-service", "cache", "redis", "oom", "jwt", "INC-203"],
        raw_text="Auth cache memory exhaustion and JWT validation latency surge.",
    )


@pytest.fixture
def mem_inc_305():
    return IncidentMemoryItem(
        id="mem-305",
        incident_id="INC-305",
        service="event-queue-worker",
        severity="HIGH",
        alert_signature="KafkaConsumerGroupLagSurgeAndPoisonPill",
        title="Kafka Worker Deserialization Poison Pill & Partition Stall",
        symptoms=[
            "Kafka consumer group lag on partition 4 surged from 20 to 520000 messages",
            "Worker threads encountering repeated RecordDeserializationException",
            "Consumer group rebalance storms occurring every 60 seconds",
        ],
        root_cause="Upstream publisher emitted corrupt Avro byte payloads missing magic byte 0x00, trapping workers in infinite retry loop.",
        failed_mitigations=["Increasing consumer thread concurrency caused all worker threads to encounter poison pill."],
        verified_runbook="RB-KAFKA-SKIP-OFFSET-TO-DLQ",
        runbook_used="RB-KAFKA-SKIP-OFFSET-TO-DLQ",
        tags=["event-queue-worker", "kafka", "poison-pill", "avro", "dlq", "INC-305"],
        raw_text="Kafka worker deserialization poison pill and partition stall.",
    )


@pytest.fixture
def mem_inc_402():
    return IncidentMemoryItem(
        id="mem-402",
        incident_id="INC-402",
        service="checkout-service",
        severity="CRITICAL",
        alert_signature="CheckoutRedisPoolExhaustionHighErrorRate",
        title="Redis Connection Pool Starvation under High Traffic Spike",
        symptoms=[
            "p99 latency spiked to 4100ms",
            "RedisConnectionClosedException in checkout logs",
            "redis_pool_wait_duration_seconds > 2.5s",
            "HTTP 503 Service Unavailable",
        ],
        root_cause="Redis client connection pool exhausted during flash sale; leaked idle connections without keep-alive timeouts.",
        failed_mitigations=["Pod restarts alone caused connection storms back into Redis master node."],
        verified_runbook="RB-REDIS-FAILOVER",
        runbook_used="RB-REDIS-FAILOVER",
        tags=["redis", "checkout-service", "connection-pool", "INC-402"],
        raw_text="Redis connection pool starvation under high traffic spike on checkout-service.",
    )


# ---------------------------------------------------------------------------
# Test 1: Existing INC-104 known alert -> accepted
# ---------------------------------------------------------------------------

def test_1_known_inc_104_accepted(mem_inc_104):
    """Test 1: Existing INC-104 known alert produces HIGH match and is accepted."""
    alert = AlertPayload(
        service="payment-api",
        title="PaymentGatewayEgressTimeoutBreached",
        description="Outbound HTTPS timeout calling Stripe payment gateway API with thread pool saturation",
        symptoms=[
            "Outbound HTTPS timeout > 30s calling Stripe payment gateway API",
            "Egress HTTP thread pool saturation across 8 replicas",
            "Cascading HTTP 504 Gateway Timeout on /api/v2/checkout/charge",
        ],
        severity=AlertSeverity.CRITICAL,
    )

    res = score_candidate_relevance(alert, mem_inc_104)
    assert res.is_accepted is True
    assert res.match_strength == MatchStrength.HIGH
    assert res.verdict == "ACCEPTED"
    assert "stripe" in res.overlap_tokens or "504" in res.overlap_tokens or "thread pool" in res.overlap_tokens


# ---------------------------------------------------------------------------
# Test 2: INC-104 paraphrase -> accepted
# ---------------------------------------------------------------------------

def test_2_inc_104_paraphrase_accepted(mem_inc_104):
    """Test 2: Paraphrased variant with alternate wording is accepted with HIGH relevance."""
    alert = AlertPayload(
        service="payment-api",
        title="Stripe Gateway Egress Latency & Worker Thread Exhaustion",
        description="Third-party payment gateway HTTP socket timeout threshold breached causing zero idle execution threads.",
        symptoms=[
            "Outbound HTTPS calls to Stripe payment gateway exceeding 35s latency budget",
            "Tomcat worker thread pool 100% busy across all payment-api replicas",
            "Cascading 504 Gateway Timeout responses on checkout charge route",
        ],
        severity=AlertSeverity.CRITICAL,
    )

    res = score_candidate_relevance(alert, mem_inc_104)
    assert res.is_accepted is True
    assert res.match_strength == MatchStrength.HIGH
    assert res.verdict == "ACCEPTED"
    assert any("High correlation" in b for b in res.evidence_bullets)


# ---------------------------------------------------------------------------
# Test 3: INC-104 TLS decoy -> rejected
# ---------------------------------------------------------------------------

def test_3_inc_104_tls_decoy_rejected(mem_inc_104):
    """Test 3: Lookalike alert on payment-api with SSL/TLS expiration is rejected as domain conflict."""
    decoy_alert = AlertPayload(
        service="payment-api",
        title="Inbound Ingress SSL Certificate Expired on Listener",
        description="Edge ingress listener SSL certificate expired on port 8443 rejecting inbound handshakes.",
        symptoms=[
            "X509CertificateExpiredException on inbound HTTPS listener",
            "TLS handshake rejection rate reaching 100% on port 8443",
            "Ingress envoy reporting local SSL verification terminated",
        ],
        severity=AlertSeverity.CRITICAL,
    )

    res = score_candidate_relevance(decoy_alert, mem_inc_104)
    assert res.is_accepted is False
    assert res.match_strength == MatchStrength.NONE
    assert res.verdict == "REJECTED_DIFFERENT_FAILURE_MODE"
    assert "security_tls" in res.alert_domains
    assert "connection_pool" in res.candidate_domains


# ---------------------------------------------------------------------------
# Test 4: PostgreSQL disk exhaustion vs deadlock -> rejected
# ---------------------------------------------------------------------------

def test_4_postgres_disk_full_vs_deadlock_rejected(mem_inc_108):
    """Test 4: Disk space critical on order-db-primary is rejected against deadlock history."""
    decoy_alert = AlertPayload(
        service="order-db-primary",
        title="Postgres Disk Space Critical & WAL Archiver Disk Full",
        description="PostgreSQL WAL archive directory reached 99.8% disk utilization causing disk full write stalls.",
        symptoms=[
            "PANIC: could not write to file pg_wal/xlog: No space left on device",
            "Disk utilization on /var/lib/postgresql/data at 99.8%",
            "Database entered read-only recovery mode rejecting all transactions",
        ],
        severity=AlertSeverity.CRITICAL,
    )

    res = score_candidate_relevance(decoy_alert, mem_inc_108)
    assert res.is_accepted is False
    assert res.match_strength == MatchStrength.NONE
    assert res.verdict == "REJECTED_DIFFERENT_FAILURE_MODE"
    assert "storage_disk" in res.alert_domains
    assert "db_locking" in res.candidate_domains


# ---------------------------------------------------------------------------
# Test 5: Redis Sentinel partition vs Redis eviction -> rejected
# ---------------------------------------------------------------------------

def test_5_redis_sentinel_partition_vs_eviction_rejected(mem_inc_203):
    """Test 5: Sentinel consensus loss on auth-cache-service is rejected against OOM eviction history."""
    decoy_alert = AlertPayload(
        service="auth-cache-service",
        title="Redis Sentinel Quorum Loss & Split Brain Network Partition",
        description="Inter-datacenter network partition preventing Redis Sentinel quorum consensus on master leadership.",
        symptoms=[
            "Sentinel cluster lost quorum across availability zone us-east-1b",
            "Multiple nodes advertising conflicting master epochs",
            "Client driver logging NoReachableMasterException",
        ],
        severity=AlertSeverity.HIGH,
    )

    res = score_candidate_relevance(decoy_alert, mem_inc_203)
    assert res.is_accepted is False
    assert res.match_strength == MatchStrength.NONE
    assert res.verdict == "REJECTED_DIFFERENT_FAILURE_MODE"
    assert "consensus_quorum" in res.alert_domains
    assert "cache_memory_eviction" in res.candidate_domains


# ---------------------------------------------------------------------------
# Test 6: Kafka mTLS handshake vs Avro poison pill -> rejected
# ---------------------------------------------------------------------------

def test_6_kafka_mtls_vs_avro_poison_pill_rejected(mem_inc_305):
    """Test 6: Broker mTLS failure on event-queue-worker is rejected against Avro poison pill history."""
    decoy_alert = AlertPayload(
        service="event-queue-worker",
        title="Kafka TLS Broker Certificate Renewal Handshake Failure",
        description="Internal mTLS authentication failure between worker pods and Kafka broker cluster.",
        symptoms=[
            "SSLHandshakeException: Received fatal alert: certificate_unknown",
            "Worker unable to authenticate to Kafka broker port 9093",
            "Kafka client SSL truststore validation failed on broker cert",
        ],
        severity=AlertSeverity.HIGH,
    )

    res = score_candidate_relevance(decoy_alert, mem_inc_305)
    assert res.is_accepted is False
    assert res.match_strength == MatchStrength.NONE
    assert res.verdict == "REJECTED_DIFFERENT_FAILURE_MODE"
    assert "security_tls" in res.alert_domains
    assert "messaging_poison_pill" in res.candidate_domains


# ---------------------------------------------------------------------------
# Test 7: Regex CPU lockup vs Redis pool exhaustion -> rejected
# ---------------------------------------------------------------------------

def test_7_regex_cpu_vs_redis_pool_rejected(mem_inc_402):
    """Test 7: ReDoS CPU peg on checkout-service is rejected against Redis pool exhaustion history."""
    decoy_alert = AlertPayload(
        service="checkout-service",
        title="Checkout Cart Regex ReDoS Vulnerability CPU Spike",
        description="Malicious payload triggering catastrophic regex backtracking on discount coupon parser.",
        symptoms=[
            "Single-threaded CPU usage pegged at 100% on coupon validation routine",
            "Regex engine stuck in exponential backtracking loop",
            "Worker thread hanging indefinitely inside java.util.regex.Pattern",
        ],
        severity=AlertSeverity.CRITICAL,
    )

    res = score_candidate_relevance(decoy_alert, mem_inc_402)
    assert res.is_accepted is False
    assert res.match_strength == MatchStrength.NONE
    assert res.verdict == "REJECTED_DIFFERENT_FAILURE_MODE"
    assert "algorithmic_cpu" in res.alert_domains
    assert "connection_pool" in res.candidate_domains


# ---------------------------------------------------------------------------
# Test 8: Novel incident -> no accepted historical precedent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_8_novel_incident_no_accepted_precedent():
    """Test 8: Unseen incident produces novelty=True and empty historical_matches."""
    novel_req = TriageRequest(
        service="search-indexing-worker",
        alert="Elasticsearch Cluster Yellow & Split-Brain Shard State",
        title="Elasticsearch Cluster Yellow & Split-Brain Shard State",
        description="Elasticsearch cluster entered yellow state with primary shards unassigned after data node dropped.",
        symptoms=[
            "Primary shard unassigned for index products_v3",
            "Node search-data-02 dropped from master node cluster state",
            "Cluster health yellow with 12 unassigned replica shards",
        ],
        severity="HIGH",
        enable_memory=True,
    )

    # Empty candidate recall simulation
    with patch.object(
        hindsight_service,
        "recall_incident_memory",
        new_callable=AsyncMock,
        return_value=RecallResultSummary(
            match_strength=MatchStrength.NONE,
            is_novel=True,
            memories_found=[],
            candidates_retrieved=[],
            evidence_bullets=["No historical incidents found in Hindsight memory for service 'search-indexing-worker'."],
            relevance_verdict="NONE",
            raw_recall_count=0,
            query_used="Service: search-indexing-worker.",
            hindsight_connected=True,
        ),
    ):
        response = await triage_engine.triage(novel_req)

        assert response.novelty is True
        assert response.historical_matches == []
        assert "No sufficiently relevant historical incident found" in response.incident_summary
        assert response.recommended_runbook is not None


# ---------------------------------------------------------------------------
# Test 9: Service-only similarity -> never HIGH
# ---------------------------------------------------------------------------

def test_9_service_only_similarity_never_high():
    """Test 9: Invariant enforcement: Service match alone with generic words must NEVER produce HIGH relevance."""
    generic_alert = AlertPayload(
        service="cart-service",
        title="Cart Service Failure And High Error Rate",
        description="Observed high error rate and client latency across multiple pods in production environment.",
        symptoms=[
            "Service error rate exceeded threshold",
            "Client request timeout observed during traffic spike",
            "Backend pod failure reported by system monitoring",
        ],
        severity=AlertSeverity.HIGH,
    )

    # Candidate with same service but only generic words
    generic_candidate = IncidentMemoryItem(
        id="mem-generic-cart",
        incident_id="INC-999",
        service="cart-service",
        title="Cart Service Incident Degradation",
        symptoms=["Service failure observed under high traffic load", "Errors reported by backend client"],
        root_cause="Generic service failure caused by elevated load.",
        raw_text="Cart service degradation and errors during elevated traffic.",
    )

    res = score_candidate_relevance(generic_alert, generic_candidate)
    assert res.match_strength != MatchStrength.HIGH
    assert res.is_accepted is False
    assert res.match_strength == MatchStrength.NONE
    assert res.verdict == "REJECTED_INSUFFICIENT_FAILURE_MODE_ALIGNMENT"


# ---------------------------------------------------------------------------
# Test 10: Existing stateless mode still bypasses memory
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_10_stateless_mode_bypasses_memory():
    """Test 10: Explicit enable_memory=False completely bypasses memory recall and returns novelty=True."""
    req = TriageRequest(
        service="payment-api",
        alert="PaymentGatewayEgressTimeoutBreached",
        title="PaymentGatewayEgressTimeoutBreached",
        description="Outbound HTTPS timeout > 30s calling Stripe payment gateway API",
        symptoms=["Outbound HTTPS timeout > 30s calling Stripe payment gateway API"],
        severity="CRITICAL",
        enable_memory=False,
    )

    with patch.object(hindsight_service, "recall_incident_memory") as mock_recall:
        response = await triage_engine.triage(req)

        # Hindsight recall should NOT have been invoked
        mock_recall.assert_not_called()

        assert response.memory_used is False
        assert response.novelty is True
        assert response.historical_matches == []
        assert "Stateless" in response.incident_summary
