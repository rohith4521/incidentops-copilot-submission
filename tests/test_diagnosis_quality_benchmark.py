"""PHASE 7.5 — Diagnosis Quality Benchmark Tests.

Validates the held-out diagnosis quality benchmark:
1. Correct root-cause scoring (deterministic family matching)
2. Accepted alias resolution (synonym and normalized alias matching)
3. Incorrect diagnosis rejection (mismatched failure domain / cause)
4. Novel incident handling (novelty preservation, zero historical grounding)
5. False historical grounding detection (hallucinated precedents on decoys/novel)
6. Memory OFF vs ON comparison (evaluating improvement and false-grounding rates)
7. Benchmark leakage prevention: Evaluation-only fields never enter LLM prompts
"""

import json
from pathlib import Path
from typing import Any, Dict, List
import pytest

from app.models.memory import IncidentMemoryItem, MatchStrength, RecallResultSummary
from app.models.runbook import RunbookRecommendation
from app.models.triage import HistoricalMatch, TriageRequest, TriageResponse
from app.services.diagnosis_benchmark import (
    BenchmarkSummary,
    ConditionScore,
    DiagnosisQualityBenchmark,
    ScenarioBenchmarkScore,
    build_isolated_triage_request,
    load_benchmark_dataset,
    score_single_condition,
)
from app.services.groq_service import groq_service

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def benchmark_dataset() -> List[Dict[str, Any]]:
    """Load the held-out diagnosis quality benchmark dataset."""
    return load_benchmark_dataset()


# ---------------------------------------------------------------------------
# Test 0: Dataset Schema & Category Composition
# ---------------------------------------------------------------------------

def test_0_dataset_schema_and_composition(benchmark_dataset: List[Dict[str, Any]]):
    """Verify that dataset contains exactly the required scenarios, categories, and fields."""
    assert len(benchmark_dataset) >= 16, f"Expected >= 16 scenarios, got {len(benchmark_dataset)}"

    categories = [s["category"] for s in benchmark_dataset]
    assert categories.count("known") == 4
    assert categories.count("paraphrased") == 4
    assert categories.count("decoy") == 4
    assert categories.count("novel") == 4

    required_fields = {
        "scenario_id",
        "category",
        "service",
        "title",
        "description",
        "symptoms",
        "severity",
        "failure_domain",
        "expected_root_cause_family",
        "acceptable_root_cause_aliases",
        "expected_runbook_family",
        "acceptable_runbook_aliases",
        "has_trusted_precedent",
    }

    for s in benchmark_dataset:
        missing = required_fields - set(s.keys())
        assert not missing, f"Scenario {s.get('scenario_id')} is missing fields: {missing}"
        assert isinstance(s["acceptable_root_cause_aliases"], list)
        assert len(s["acceptable_root_cause_aliases"]) >= 1
        assert isinstance(s["acceptable_runbook_aliases"], list)
        if s["has_trusted_precedent"]:
            assert "expected_precedent_id" in s
            assert s["expected_precedent_id"] is not None


# ---------------------------------------------------------------------------
# Test 1: Correct Root Cause Deterministic Scoring
# ---------------------------------------------------------------------------

def test_1_correct_root_cause():
    """Verify deterministic scoring marks exact root-cause family as correct."""
    scenario = {
        "scenario_id": "TEST-01",
        "category": "known",
        "expected_root_cause_family": "kafka consumer group lag",
        "acceptable_root_cause_aliases": ["rebalance storm", "consumer lag"],
        "expected_runbook_family": "RB-STREAM-CONSUMER-SCALE",
        "acceptable_runbook_aliases": ["consumer scale"],
        "has_trusted_precedent": True,
        "expected_precedent_id": "INC-104",
    }

    response = TriageResponse(
        incident_summary="Incident detected in stream pipeline.",
        likely_root_cause="High Kafka consumer group lag due to skewed partition processing.",
        reasoning_summary="Partition skew identified.",
        memory_used=True,
        recommended_runbook=RunbookRecommendation(
            runbook_id="RB-STREAM-CONSUMER-SCALE",
            title="Scale stream consumer pods",
            justification="Scale partition consumers",
            blast_radius_analysis="Bounded to consumer pods",
            historical_reference_id="INC-104",
            actions=[],
        ),
        historical_matches=[
            HistoricalMatch(incident_id="INC-104", service="stream-service", title="Kafka rebalance storm", match_strength="High")
        ],
        novelty=False,
    )

    score = score_single_condition(scenario, response, condition="MEMORY_ON")
    assert score.diagnosis_correct is True
    assert score.runbook_correct is True
    assert score.retrieval_correct is True
    assert score.precedent_used is True
    assert score.false_historical_grounding is False


# ---------------------------------------------------------------------------
# Test 2: Accepted Aliases Scoring
# ---------------------------------------------------------------------------

def test_2_accepted_aliases():
    """Verify deterministic scoring accepts synonyms and aliases even when family string is absent."""
    scenario = {
        "scenario_id": "TEST-02",
        "category": "paraphrased",
        "expected_root_cause_family": "database connection pool starvation",
        "acceptable_root_cause_aliases": ["pool exhaustion", "hikari pool exhaustion", "pg pool limit reached"],
        "expected_runbook_family": "RB-DB-POOL-SCALE",
        "acceptable_runbook_aliases": ["pool scale", "database pool expand"],
        "has_trusted_precedent": True,
        "expected_precedent_id": "INC-203",
    }

    response = TriageResponse(
        incident_summary="Checkout database connections saturated.",
        likely_root_cause="Hikari pool exhaustion preventing new queries from acquiring a lease.",
        reasoning_summary="Pool saturation identified.",
        memory_used=True,
        recommended_runbook=RunbookRecommendation(
            runbook_id="RB-DATABASE-POOL-EXPAND",
            title="Expand database connection pool",
            justification="Mitigates connection exhaustion",
            blast_radius_analysis="Pool connection increase bounded by max_connections",
            historical_reference_id="INC-203",
            actions=[],
        ),
        historical_matches=[
            HistoricalMatch(incident_id="INC-203", service="order-service", title="Pool exhaustion incident", match_strength="High")
        ],
        novelty=False,
    )

    score = score_single_condition(scenario, response, condition="MEMORY_ON")
    assert score.diagnosis_correct is True  # Matched "hikari pool exhaustion"
    assert score.runbook_correct is True    # Matched "database pool expand" alias
    assert score.retrieval_correct is True
    assert score.false_historical_grounding is False


# ---------------------------------------------------------------------------
# Test 3: Incorrect Diagnosis Rejection
# ---------------------------------------------------------------------------

def test_3_incorrect_diagnosis():
    """Verify deterministic scoring marks incorrect diagnosis and runbook as False."""
    scenario = {
        "scenario_id": "TEST-03",
        "category": "known",
        "expected_root_cause_family": "redis eviction maxmemory exhaustion",
        "acceptable_root_cause_aliases": ["oom-kill", "redis memory limit"],
        "expected_runbook_family": "RB-CACHE-MEMORY-EXPAND",
        "acceptable_runbook_aliases": ["redis flush expired", "cache resize"],
        "has_trusted_precedent": True,
        "expected_precedent_id": "INC-305",
    }

    # Irrelevant diagnosis (claiming network DNS failure)
    response = TriageResponse(
        incident_summary="CoreDNS resolution timeout on cluster nodes.",
        likely_root_cause="Upstream DNS server dropped UDP packets causing DNS resolution failures.",
        reasoning_summary="DNS timeout observed.",
        memory_used=False,
        recommended_runbook=RunbookRecommendation(
            runbook_id="RB-DNS-RESTART",
            title="Restart CoreDNS daemonset",
            justification="Restart DNS pods",
            blast_radius_analysis="Rolling restart with minimal DNS interruption",
            historical_reference_id=None,
            actions=[],
        ),
        historical_matches=[],
        novelty=True,
    )

    score = score_single_condition(scenario, response, condition="MEMORY_OFF")
    assert score.diagnosis_correct is False
    assert score.runbook_correct is False
    assert score.retrieval_correct is False  # Expected INC-305 but got none


# ---------------------------------------------------------------------------
# Test 4: Novel Incident Handling
# ---------------------------------------------------------------------------

def test_4_novel_incident():
    """Verify novel incident evaluation preserves novelty and produces zero false grounding."""
    scenario = {
        "scenario_id": "TEST-04",
        "category": "novel",
        "service": "billing-service",
        "expected_root_cause_family": "ebpf bytecode kernel verification failure",
        "acceptable_root_cause_aliases": ["ebpf verifier rejected", "bpf filter error"],
        "expected_runbook_family": "NONE",
        "acceptable_runbook_aliases": ["novel-incident-investigation", "manual sre escalation"],
        "has_trusted_precedent": False,
        "expected_precedent_id": None,
    }

    response = TriageResponse(
        incident_summary="No sufficiently relevant historical incident found. Novel kernel filter error.",
        likely_root_cause="eBPF bytecode kernel verification failure during socket probe attachment.",
        reasoning_summary="First-principles eBPF analysis.",
        memory_used=True,
        recommended_runbook=RunbookRecommendation(
            runbook_id="RB-NOVEL-INCIDENT-INVESTIGATION",
            title="Manual SRE escalation for kernel anomaly",
            justification="No historical precedent; first-principles triage",
            blast_radius_analysis="Investigation only, non-destructive",
            historical_reference_id=None,
            actions=[],
        ),
        historical_matches=[],
        novelty=True,
    )

    score = score_single_condition(scenario, response, condition="MEMORY_ON")
    assert score.diagnosis_correct is True
    assert score.retrieval_correct is True   # Correctly retrieved 0 historical matches
    assert score.precedent_used is False
    assert score.false_historical_grounding is False
    assert score.novel_false_grounding is False


# ---------------------------------------------------------------------------
# Test 5: False Historical Grounding Detection
# ---------------------------------------------------------------------------

def test_5_false_historical_grounding():
    """Verify scorer flags false historical grounding on lookalike decoys and novel alerts."""
    # Lookalike decoy scenario: Looks like Kafka lag, but is actually bad schema parsing
    scenario_decoy = {
        "scenario_id": "TEST-05A",
        "category": "decoy",
        "service": "stream-consumer",
        "expected_root_cause_family": "avro schema deserialization failure",
        "acceptable_root_cause_aliases": ["schema mismatch", "poison pill payload"],
        "expected_runbook_family": "RB-SCHEMA-POISON-PILL-DLQ",
        "acceptable_runbook_aliases": ["quarantine poison message"],
        "has_trusted_precedent": False,
        "expected_precedent_id": None,
    }

    # Hallucinated / falsely grounded response matching historical INC-104
    hallucinated_response = TriageResponse(
        incident_summary="Matches historical incident INC-104 Kafka rebalance storm.",
        likely_root_cause="Kafka consumer partition rebalance lag.",
        reasoning_summary="Historical incident matches.",
        memory_used=True,
        recommended_runbook=RunbookRecommendation(
            runbook_id="RB-STREAM-CONSUMER-SCALE",
            title="Scale stream consumer pods",
            justification="Historical precedent INC-104 recommends scaling consumers",
            blast_radius_analysis="Bounded to consumer pods",
            historical_reference_id="INC-104",
            actions=[],
        ),
        historical_matches=[
            HistoricalMatch(incident_id="INC-104", service="stream-service", title="Kafka rebalance storm", match_strength="High")
        ],
        novelty=False,
    )

    score_decoy = score_single_condition(scenario_decoy, hallucinated_response, condition="MEMORY_ON")
    assert score_decoy.false_historical_grounding is True
    assert score_decoy.retrieval_correct is False

    # Also test on a novel scenario
    scenario_novel = {
        "scenario_id": "TEST-05B",
        "category": "novel",
        "service": "auth-service",
        "expected_root_cause_family": "clock drift jwt nbf rejection",
        "acceptable_root_cause_aliases": ["ntp clock skew", "jwt not before future timestamp"],
        "expected_runbook_family": "NONE",
        "acceptable_runbook_aliases": ["ntp resync"],
        "has_trusted_precedent": False,
        "expected_precedent_id": None,
    }

    score_novel = score_single_condition(scenario_novel, hallucinated_response, condition="MEMORY_ON")
    assert score_novel.false_historical_grounding is True
    assert score_novel.novel_false_grounding is True


# ---------------------------------------------------------------------------
# Test 6: Memory OFF vs Memory ON Comparison
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_6_memory_off_vs_on_comparison():
    """Verify benchmark engine compares Memory OFF and Memory ON conditions systematically."""

    class MockTriageEngine:
        async def triage(self, request: TriageRequest) -> TriageResponse:
            if not request.enable_memory:
                # Stateless first-principles triage: can diagnose root cause from symptoms,
                # but cannot recommend specific verified historical runbooks or reference IDs.
                return TriageResponse(
                    incident_summary="No sufficiently relevant historical incident found.",
                    likely_root_cause=f"Identified {request.alert_title} issue from symptoms.",
                    reasoning_summary="Stateless first-principles reasoning.",
                    memory_used=False,
                    recommended_runbook=RunbookRecommendation(
                        runbook_id="RB-GENERIC-FIRST-PRINCIPLES",
                        title="Generic remediation",
                        justification="First principles",
                        blast_radius_analysis="Low risk baseline",
                        historical_reference_id=None,
                        actions=[],
                    ),
                    historical_matches=[],
                    novelty=True,
                )
            else:
                # Memory ON: Returns verified historical runbook if precedent exists
                if "kafka" in request.alert_title.lower() or "stream" in request.service.lower():
                    return TriageResponse(
                        incident_summary="Matched historical incident INC-104.",
                        likely_root_cause="Kafka consumer group lag partition rebalance.",
                        reasoning_summary="Recalled historical precedent INC-104.",
                        memory_used=True,
                        recommended_runbook=RunbookRecommendation(
                            runbook_id="RB-STREAM-CONSUMER-SCALE",
                            title="Scale stream consumer pods",
                            justification="Verified from INC-104",
                            blast_radius_analysis="Bounded to consumer pods",
                            historical_reference_id="INC-104",
                            actions=[],
                        ),
                        historical_matches=[
                            HistoricalMatch(incident_id="INC-104", service="stream-service", title="Kafka storm", match_strength="High")
                        ],
                        novelty=False,
                    )
                else:
                    return TriageResponse(
                        incident_summary="No sufficiently relevant historical incident found.",
                        likely_root_cause=f"Analyzed {request.alert_title}.",
                        reasoning_summary="No precedent match reasoning.",
                        memory_used=True,
                        recommended_runbook=None,
                        historical_matches=[],
                        novelty=True,
                    )

    mock_engine = MockTriageEngine()
    test_scenarios = [
        {
            "scenario_id": "TEST-KNOWN-01",
            "category": "known",
            "service": "stream-service",
            "title": "Kafka partition lag alert",
            "expected_root_cause_family": "kafka consumer group lag",
            "acceptable_root_cause_aliases": ["partition lag"],
            "expected_runbook_family": "RB-STREAM-CONSUMER-SCALE",
            "acceptable_runbook_aliases": ["consumer scale"],
            "has_trusted_precedent": True,
            "expected_precedent_id": "INC-104",
        },
        {
            "scenario_id": "TEST-NOVEL-01",
            "category": "novel",
            "service": "billing-service",
            "title": "Unseen quantum cryptographic sync fault",
            "expected_root_cause_family": "quantum sync fault",
            "acceptable_root_cause_aliases": ["crypto sync"],
            "expected_runbook_family": "NONE",
            "acceptable_runbook_aliases": ["escalate"],
            "has_trusted_precedent": False,
            "expected_precedent_id": None,
        },
    ]

    benchmark = DiagnosisQualityBenchmark(engine=mock_engine, dataset=test_scenarios)
    summary: BenchmarkSummary = await benchmark.run_benchmark()

    assert summary.dataset_size == 2
    # In known case, Memory ON provided verified runbook (RB-STREAM-CONSUMER-SCALE)
    assert summary.runbook_accuracy_on > summary.runbook_accuracy_off
    assert summary.absolute_runbook_improvement == 50.0  # 1 of 2 cases gained runbook accuracy
    # In novel case, Memory ON maintained 0% false grounding
    assert summary.novel_false_grounding_rate_on == 0.0
    assert summary.novel_false_grounding_rate_off == 0.0


# ---------------------------------------------------------------------------
# Test 7: Evaluation Fields Never Enter LLM Prompt (Leakage Prevention)
# ---------------------------------------------------------------------------

def test_7_evaluation_fields_never_enter_llm_prompt(benchmark_dataset: List[Dict[str, Any]]):
    """Verify benchmark leakage prevention: Ground truth fields are strictly isolated from prompts."""
    ground_truth_keys = [
        "expected_root_cause_family",
        "acceptable_root_cause_aliases",
        "expected_runbook_family",
        "acceptable_runbook_aliases",
        "has_trusted_precedent",
        "expected_precedent_id",
    ]

    for scenario in benchmark_dataset:
        # 1. Verify isolated TriageRequest contains none of the evaluation ground-truth fields
        req_off = build_isolated_triage_request(scenario, enable_memory=False)
        req_on = build_isolated_triage_request(scenario, enable_memory=True)

        req_off_dict = req_off.model_dump()
        req_on_dict = req_on.model_dump()

        for key in ground_truth_keys:
            assert key not in req_off_dict, f"Evaluation key '{key}' leaked into TriageRequest (off)"
            assert key not in req_on_dict, f"Evaluation key '{key}' leaked into TriageRequest (on)"

        # 2. Inspect prompts constructed for Groq/LLM layer under Memory OFF and Memory ON
        prompt_off = groq_service._build_core_triage_prompt(req_off, recall_summary=None, enable_memory=False)

        mock_recall = RecallResultSummary(
            match_strength=MatchStrength.HIGH if scenario["has_trusted_precedent"] else MatchStrength.NONE,
            is_novel=not scenario["has_trusted_precedent"],
            memories_found=[
                IncidentMemoryItem(
                    id=scenario.get("expected_precedent_id", "INC-999"),
                    incident_id=scenario.get("expected_precedent_id", "INC-999"),
                    service=scenario["service"],
                    title="Historical postmortem reference",
                    root_cause="Documented historical cause",
                    failed_mitigations=[],
                    verified_runbook="RB-SAMPLE",
                )
            ] if scenario["has_trusted_precedent"] else [],
            evidence_bullets=["Historical precedent match."],
            query_used=scenario["title"],
            hindsight_connected=True,
        )
        prompt_on = groq_service._build_core_triage_prompt(req_on, recall_summary=mock_recall, enable_memory=True)

        # None of the evaluation field names should ever be present in the prompt
        for key in ground_truth_keys:
            assert key not in prompt_off, f"Evaluation key '{key}' leaked into Memory OFF prompt!"
            assert key not in prompt_on, f"Evaluation key '{key}' leaked into Memory ON prompt!"

        # Ensure ground truth answers that are unique to the benchmark (e.g. expected_runbook_family when not mentioned in symptoms)
        expected_rf = scenario.get("expected_runbook_family")
        if expected_rf and expected_rf not in (scenario.get("title", "") + scenario.get("description", "")):
            assert expected_rf not in prompt_off, f"Runbook ground truth '{expected_rf}' leaked into OFF prompt!"


# ---------------------------------------------------------------------------
# PHASE 7.5B — Decoy False Grounding & Unseen Lookalike Regression Tests
# ---------------------------------------------------------------------------

@pytest.fixture
def seed_incident_map() -> Dict[str, IncidentMemoryItem]:
    """Load canonical seed incidents as IncidentMemoryItem models."""
    seed_path = PROJECT_ROOT / "app" / "data" / "seed_incidents.json"
    with open(seed_path, "r", encoding="utf-8") as f:
        seeds = json.load(f)
    result = {}
    for s in seeds:
        iid = s["incident_id"]
        result[iid] = IncidentMemoryItem(
            id=iid,
            incident_id=iid,
            service=s["service"],
            title=s["title"],
            root_cause=s["root_cause"],
            verified_runbook=s["verified_runbook"],
            resolution=s.get("resolution"),
            symptoms=s.get("symptoms", []),
            tags=s.get("tags", []),
            memory_status="VERIFIED",
            source_type="HUMAN_VERIFIED",
            verified_by="sre-core-team",
        )
    return result


def test_8_decoy_011_sentinel_quorum_loss_rejected_against_redis_pool(
    benchmark_dataset: List[Dict[str, Any]],
    seed_incident_map: Dict[str, IncidentMemoryItem],
):
    """Regression Test 8: BENCH-DECOY-011 (consensus_quorum) is rejected against INC-402 (connection_pool)."""
    scenario_11 = next(s for s in benchmark_dataset if s["scenario_id"] == "BENCH-DECOY-011")
    cand_402 = seed_incident_map["INC-402"]

    from app.models.alert import AlertPayload, AlertSeverity
    from app.services.relevance_scorer import evaluate_batch_relevance, score_candidate_relevance

    alert = AlertPayload(
        service=scenario_11["service"],
        title=scenario_11["title"],
        description=scenario_11["description"],
        symptoms=scenario_11["symptoms"],
        severity=AlertSeverity.HIGH,
    )

    res = score_candidate_relevance(alert, cand_402)
    assert res.is_accepted is False
    assert res.match_strength == MatchStrength.NONE
    assert res.verdict in ("REJECTED_DIFFERENT_FAILURE_MODE", "REJECTED_NO_ALIGNMENT")

    # In batch relevance, no historical memories may be accepted
    strength, bullets, accepted_items, verdict, reason = evaluate_batch_relevance(alert, [cand_402])
    assert strength == MatchStrength.NONE
    assert len(accepted_items) == 0


def test_9_decoy_012_redos_cpu_rejected_against_kafka_poison_pill(
    benchmark_dataset: List[Dict[str, Any]],
    seed_incident_map: Dict[str, IncidentMemoryItem],
):
    """Regression Test 9: BENCH-DECOY-012 (ReDoS) with 'without deserialization errors' rejects INC-305."""
    scenario_12 = next(s for s in benchmark_dataset if s["scenario_id"] == "BENCH-DECOY-012")
    cand_305 = seed_incident_map["INC-305"]

    from app.models.alert import AlertPayload, AlertSeverity
    from app.services.relevance_scorer import evaluate_batch_relevance, score_candidate_relevance

    alert = AlertPayload(
        service=scenario_12["service"],
        title=scenario_12["title"],
        description=scenario_12["description"],
        symptoms=scenario_12["symptoms"],
        severity=AlertSeverity.HIGH,
    )

    res = score_candidate_relevance(alert, cand_305)
    assert res.is_accepted is False
    assert res.match_strength == MatchStrength.NONE
    assert res.verdict == "REJECTED_DIFFERENT_FAILURE_MODE"

    # Batch relevance rejects
    strength, bullets, accepted_items, verdict, reason = evaluate_batch_relevance(alert, [cand_305])
    assert strength == MatchStrength.NONE
    assert len(accepted_items) == 0


def test_10_unseen_lookalike_1_bpf_filter_vs_db_deadlock_rejected(
    seed_incident_map: Dict[str, IncidentMemoryItem],
):
    """Regression Test 10: Unseen lookalike pattern 1 (eBPF verifier on DB host) is rejected against INC-108 (deadlock)."""
    cand_108 = seed_incident_map["INC-108"]

    from app.models.alert import AlertPayload, AlertSeverity
    from app.services.relevance_scorer import evaluate_batch_relevance, score_candidate_relevance

    # Unseen alert sharing service order-db-primary, with negated mention of deadlocks
    unseen_alert = AlertPayload(
        service="order-db-primary",
        title="BPF Socket Probe Verifier Failure on Database Host",
        description="eBPF verifier rejected telemetry probe program with unbounded loop instruction limit breached.",
        symptoms=[
            "bpf_probe_attach failed with EPERM verifier error",
            "Kernel verifier log: back-edge from insn 412 to 105 detected",
            "Database engine operating normally without 40p01 deadlocks observed",
            "Host network socket monitoring disabled by daemon failure",
        ],
        severity=AlertSeverity.HIGH,
    )

    res = score_candidate_relevance(unseen_alert, cand_108)
    assert res.is_accepted is False
    assert res.match_strength == MatchStrength.NONE
    assert res.verdict in ("REJECTED_DIFFERENT_FAILURE_MODE", "REJECTED_INSUFFICIENT_FAILURE_MODE_ALIGNMENT", "REJECTED_NO_ALIGNMENT")

    strength, bullets, accepted_items, verdict, reason = evaluate_batch_relevance(unseen_alert, [cand_108])
    assert strength == MatchStrength.NONE
    assert len(accepted_items) == 0


def test_11_unseen_lookalike_2_jwt_clock_drift_vs_jwt_cache_oom_rejected(
    seed_incident_map: Dict[str, IncidentMemoryItem],
):
    """Regression Test 11: Unseen lookalike pattern 2 (NTP clock drift) is rejected against INC-203 (cache OOM)."""
    cand_203 = seed_incident_map["INC-203"]

    from app.models.alert import AlertPayload, AlertSeverity
    from app.services.relevance_scorer import evaluate_batch_relevance, score_candidate_relevance

    # Unseen alert sharing service auth-cache-service, but caused by clock drift rather than cache OOM
    unseen_alert = AlertPayload(
        service="auth-cache-service",
        title="NTP Daemon Clock Drift Causing Immediate JWT Token Rejection",
        description="Host clock desynchronization of +45 seconds causing valid JWT tokens to be rejected with nbf in the future.",
        symptoms=[
            "JWTVerificationException: The token cannot be used before future timestamp",
            "NTP daemon reports 45100ms offset from pool.ntp.org stratum servers",
            "Redis cache memory usage stable at 35% without OOM errors",
            "HTTP 401 Unauthorized spiked on token validation endpoint",
        ],
        severity=AlertSeverity.HIGH,
    )

    res = score_candidate_relevance(unseen_alert, cand_203)
    assert res.is_accepted is False
    assert res.match_strength == MatchStrength.NONE
    assert res.verdict in ("REJECTED_DIFFERENT_FAILURE_MODE", "REJECTED_INSUFFICIENT_FAILURE_MODE_ALIGNMENT", "REJECTED_NO_ALIGNMENT")

    strength, bullets, accepted_items, verdict, reason = evaluate_batch_relevance(unseen_alert, [cand_203])
    assert strength == MatchStrength.NONE
    assert len(accepted_items) == 0


def test_12_verified_and_paraphrased_precedents_still_accepted(
    benchmark_dataset: List[Dict[str, Any]],
    seed_incident_map: Dict[str, IncidentMemoryItem],
):
    """Regression Test 12: Verified known and paraphrased precedents remain accepted with HIGH match strength."""
    from app.models.alert import AlertPayload, AlertSeverity
    from app.services.relevance_scorer import score_candidate_relevance

    # 1. Known incident 1 (BENCH-KNOWN-001 vs INC-104)
    s1 = next(s for s in benchmark_dataset if s["scenario_id"] == "BENCH-KNOWN-001")
    alert_known = AlertPayload(
        service=s1["service"],
        title=s1["title"],
        description=s1["description"],
        symptoms=s1["symptoms"],
        severity=AlertSeverity.HIGH,
    )
    res_known = score_candidate_relevance(alert_known, seed_incident_map["INC-104"])
    assert res_known.is_accepted is True
    assert res_known.match_strength == MatchStrength.HIGH
    assert res_known.verdict == "ACCEPTED"

    # 2. Paraphrased incident 5 (BENCH-PARA-005 vs INC-402)
    s5 = next(s for s in benchmark_dataset if s["scenario_id"] == "BENCH-PARA-005")
    alert_para = AlertPayload(
        service=s5["service"],
        title=s5["title"],
        description=s5["description"],
        symptoms=s5["symptoms"],
        severity=AlertSeverity.HIGH,
    )
    res_para = score_candidate_relevance(alert_para, seed_incident_map["INC-402"])
    assert res_para.is_accepted is True
    assert res_para.match_strength == MatchStrength.HIGH
    assert res_para.verdict == "ACCEPTED"


def test_13_novel_incidents_still_rejected(
    benchmark_dataset: List[Dict[str, Any]],
    seed_incident_map: Dict[str, IncidentMemoryItem],
):
    """Regression Test 13: Completely novel incidents reject all candidates with zero false grounding."""
    from app.models.alert import AlertPayload, AlertSeverity
    from app.services.relevance_scorer import evaluate_batch_relevance

    novel_scenarios = [s for s in benchmark_dataset if s["category"] == "novel"]
    all_seeds = list(seed_incident_map.values())

    for ns in novel_scenarios:
        alert = AlertPayload(
            service=ns["service"],
            title=ns["title"],
            description=ns["description"],
            symptoms=ns["symptoms"],
            severity=AlertSeverity.HIGH,
        )
        strength, bullets, accepted_items, verdict, reason = evaluate_batch_relevance(alert, all_seeds)
        assert strength == MatchStrength.NONE, f"Novel scenario {ns['scenario_id']} falsely produced {strength}"
        assert len(accepted_items) == 0, f"Novel scenario {ns['scenario_id']} accepted memories: {accepted_items}"


@pytest.mark.asyncio
async def test_14_raw_candidates_remain_distinguishable_from_accepted_memories(
    seed_incident_map: Dict[str, IncidentMemoryItem],
):
    """Regression Test 14: Raw candidates remain distinguishable from accepted trusted memories."""
    from app.models.alert import AlertPayload, AlertSeverity
    from app.services.hindsight_service import hindsight_service
    from app.services.triage_engine import triage_engine
    from unittest.mock import AsyncMock, patch

    # Decoy alert for auth-cache-service
    decoy_req = TriageRequest(
        service="auth-cache-service",
        alert="Redis Sentinel Quorum Loss and Split-Brain Partition",
        title="Redis Sentinel Quorum Loss and Split-Brain Partition",
        description="Network split between availability zones preventing Redis Sentinel cluster quorum.",
        symptoms=["NoReachableMasterException reported by Sentinel client"],
        severity="HIGH",
        enable_memory=True,
    )

    # Simulate Hindsight returning a lookalike raw candidate (INC-402)
    mock_raw_candidate = seed_incident_map["INC-402"]

    # When evaluate_batch_relevance runs, INC-402 must be rejected
    from app.services.relevance_scorer import evaluate_batch_relevance
    alert_payload = AlertPayload(
        service=decoy_req.service,
        title=decoy_req.alert_title,
        description=decoy_req.description,
        symptoms=decoy_req.normalized_symptoms,
        severity=AlertSeverity.HIGH,
    )
    strength, bullets, accepted, verdict, reason = evaluate_batch_relevance(alert_payload, [mock_raw_candidate])
    assert strength == MatchStrength.NONE
    assert accepted == []

    mock_summary = RecallResultSummary(
        match_strength=strength,
        is_novel=True,
        memories_found=accepted,  # Strictly empty!
        candidates_retrieved=[mock_raw_candidate],  # Raw candidate traced!
        evidence_bullets=bullets,
        relevance_verdict=verdict,
        query_used=decoy_req.alert_title,
        hindsight_connected=True,
    )

    with patch.object(hindsight_service, "recall_incident_memory", new_callable=AsyncMock, return_value=mock_summary):
        response = await triage_engine.triage(decoy_req)

        # 1. Raw candidate was retained for auditability
        assert len(response.candidates_recalled) == 1
        assert response.candidates_recalled[0].incident_id == "INC-402"

        # 2. But trusted historical matches are strictly empty
        assert response.historical_matches == []

        # 3. Novelty is preserved without false grounding
        assert response.novelty is True
        assert "No sufficiently relevant historical incident found" in response.incident_summary

