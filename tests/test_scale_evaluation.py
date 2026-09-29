"""PHASE 6.7A — Scale Evaluation Tests.

Validates the scale evaluation benchmark:
1. At least 200 incidents are generated across multiple services and domains
2. All generated incidents satisfy the memory schema and trust validation
3. Benchmark produces p50/p95 latency distributions for recall and relevance
4. Candidate and accepted precedent counts are recorded
5. Decoy evaluation is recorded with false-match rate and specificity
6. Benchmark is deterministic with a fixed seed
"""

import json
from pathlib import Path
import pytest
from typing import Any, Dict, List

from app.models.memory import (
    IncidentMemoryItem,
    MemorySourceType,
    MemoryStatus,
    RetainIncidentPayload,
)
from app.services.provenance_service import provenance_service
from scripts.evaluate_scale_memory import (
    FAILURE_DOMAIN_TEMPLATES,
    SERVICES,
    generate_scale_incidents,
    generate_scale_scenarios,
    run_scale_benchmark,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Test 1: At Least 200 Incidents Are Generated
# ---------------------------------------------------------------------------

def test_1_at_least_200_incidents_are_generated():
    """Verify that generator produces >= 200 distinct incidents across services and domains."""
    incidents = generate_scale_incidents(count=200, seed=42)
    assert len(incidents) >= 200, f"Expected >= 200 incidents, got {len(incidents)}"

    # Check distinct incident IDs
    incident_ids = {inc.incident_id for inc in incidents}
    assert len(incident_ids) == len(incidents), "Duplicate incident IDs detected in generated corpus"

    # Check multiple services covered
    services_covered = {inc.service for inc in incidents}
    assert len(services_covered) >= 8, f"Expected at least 8 services, got {len(services_covered)}"

    # Check multiple failure domains covered
    domains_covered = {inc.tags[1] for inc in incidents}
    assert len(domains_covered) >= 6, f"Expected at least 6 failure domains, got {len(domains_covered)}"


# ---------------------------------------------------------------------------
# Test 2: All Generated Incidents Satisfy Memory Schema
# ---------------------------------------------------------------------------

def test_2_all_generated_incidents_satisfy_memory_schema():
    """Verify all generated incidents strictly conform to Pydantic memory schemas and trust invariants."""
    incidents = generate_scale_incidents(count=200, seed=42)

    for inc in incidents:
        # Schema instance check
        assert isinstance(inc, IncidentMemoryItem)
        assert inc.id.startswith("mem-")
        assert inc.incident_id.startswith("INC-SCALE-")
        assert inc.service in SERVICES
        assert inc.severity in ("CRITICAL", "HIGH", "MEDIUM")
        assert len(inc.symptoms) >= 2
        assert len(inc.root_cause) > 10
        assert len(inc.failed_mitigations) >= 1
        assert inc.verified_runbook.startswith("RB-")
        assert inc.memory_status == MemoryStatus.VERIFIED
        assert inc.source_type == MemorySourceType.HUMAN_VERIFIED
        assert inc.verified_by is not None

        # Verify through provenance validation boundary
        payload = RetainIncidentPayload(
            incident_id=inc.incident_id,
            service=inc.service,
            severity=inc.severity,
            alert_signature=inc.alert_signature or "",
            title=inc.title,
            symptoms=inc.symptoms,
            root_cause=inc.root_cause,
            failed_mitigations=inc.failed_mitigations,
            verified_runbook=inc.verified_runbook,
            postmortem_summary=inc.postmortem_summary or inc.title,
            tags=inc.tags,
            memory_status=inc.memory_status,
            source_type=inc.source_type,
            verified_by=inc.verified_by,
        )
        validated = provenance_service.validate_provenance_on_retention(payload)
        assert validated.memory_status == MemoryStatus.VERIFIED

        # Trust invariant verification
        assert provenance_service.is_trusted(inc) is True


# ---------------------------------------------------------------------------
# Test 3: Benchmark Produces p50/p95 Latency
# ---------------------------------------------------------------------------

def test_3_benchmark_produces_p50_p95_latency():
    """Verify that scale benchmark calculates valid p50 and p95 latencies across all components."""
    metrics = run_scale_benchmark(incident_count=200, seed=42)
    latencies = metrics["latencies"]

    required_keys = [
        "hindsight_recall_p50_ms",
        "hindsight_recall_p95_ms",
        "relevance_evaluation_p50_ms",
        "relevance_evaluation_p95_ms",
        "total_triage_latency_p50_ms",
        "total_triage_latency_p95_ms",
    ]

    for k in required_keys:
        assert k in latencies, f"Missing latency metric: {k}"
        assert isinstance(latencies[k], float)
        assert latencies[k] >= 0.0

    # p50 must be <= p95 for each dimension
    assert latencies["hindsight_recall_p50_ms"] <= latencies["hindsight_recall_p95_ms"]
    assert latencies["relevance_evaluation_p50_ms"] <= latencies["relevance_evaluation_p95_ms"]
    assert latencies["total_triage_latency_p50_ms"] <= latencies["total_triage_latency_p95_ms"]


# ---------------------------------------------------------------------------
# Test 4: Candidate and Accepted Counts Are Recorded
# ---------------------------------------------------------------------------

def test_4_candidate_and_accepted_counts_are_recorded():
    """Verify that average and maximum candidate and accepted counts are recorded."""
    metrics = run_scale_benchmark(incident_count=200, seed=42)
    counts = metrics["candidate_counts"]

    assert "avg_candidates_per_recall" in counts
    assert "max_candidates_per_recall" in counts
    assert "avg_accepted_per_recall" in counts
    assert "max_accepted_per_recall" in counts

    assert counts["avg_candidates_per_recall"] > 0
    assert counts["max_candidates_per_recall"] >= counts["avg_candidates_per_recall"]
    assert counts["avg_accepted_per_recall"] >= 0
    assert counts["max_accepted_per_recall"] >= counts["avg_accepted_per_recall"]


# ---------------------------------------------------------------------------
# Test 5: Decoy Evaluation Is Recorded
# ---------------------------------------------------------------------------

def test_5_decoy_evaluation_is_recorded():
    """Verify decoy false-match rate and specificity are calculated and recorded."""
    metrics = run_scale_benchmark(incident_count=200, seed=42)
    perf = metrics["retrieval_and_decoy_performance"]

    assert "decoy_false_match_rate" in perf
    assert "decoy_false_match_count" in perf
    assert "decoy_specificity_rate" in perf
    assert "decoy_correct_rejection_count" in perf
    assert "relevant_precedent_retrieval_rate" in perf
    assert "novel_false_match_rate" in perf

    # Decoy false match rate must be bounded (< 0.10) and specificity high (>= 0.90)
    assert perf["decoy_false_match_rate"] == 0.0
    assert perf["decoy_specificity_rate"] == 1.0
    assert perf["relevant_precedent_retrieval_rate"] >= 0.90
    assert perf["novel_false_match_rate"] == 0.0

    # Check raw counts format
    assert "/" in perf["decoy_false_match_count"]
    assert "/" in perf["decoy_correct_rejection_count"]


# ---------------------------------------------------------------------------
# Test 6: Benchmark Is Deterministic With a Fixed Seed
# ---------------------------------------------------------------------------

def test_6_benchmark_is_deterministic_with_fixed_seed():
    """Verify benchmark produces identical results when executed with the same seed."""
    run_1 = run_scale_benchmark(incident_count=200, seed=42)
    run_2 = run_scale_benchmark(incident_count=200, seed=42)

    # Incident count and scenario count match
    assert run_1["incident_count"] == run_2["incident_count"]
    assert run_1["scenario_count"] == run_2["scenario_count"]

    # Retrieval and decoy metrics match exactly
    perf_1 = run_1["retrieval_and_decoy_performance"]
    perf_2 = run_2["retrieval_and_decoy_performance"]
    assert perf_1 == perf_2

    # Candidate counts match exactly
    assert run_1["candidate_counts"] == run_2["candidate_counts"]

    # Incidents generated are structurally identical
    inc_1 = generate_scale_incidents(count=200, seed=42)
    inc_2 = generate_scale_incidents(count=200, seed=42)
    assert [i.model_dump() for i in inc_1] == [i.model_dump() for i in inc_2]
