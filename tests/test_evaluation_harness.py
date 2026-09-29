"""Automated tests for the Phase 5.1 Memory Value Evaluation Harness."""

import json
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.triage import HistoricalMatch, TriageResponse
from app.models.runbook import RunbookRecommendation, RunbookAction
from scripts.evaluate_memory import (
    calculate_metrics,
    evaluate_single_run,
    generate_markdown_report,
    load_dataset,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_dataset_structure_and_schema():
    """Verify evaluation dataset contains 5 families, 2 variants each, 1 decoy each, and >=5 novel."""
    dataset_path = PROJECT_ROOT / "app" / "data" / "eval_dataset.json"
    dataset = load_dataset(dataset_path)

    assert len(dataset) >= 20, f"Expected at least 20 cases, got {len(dataset)}"

    # Check required fields
    required_keys = {"case_id", "service", "title", "severity", "description", "symptoms", "variant_type"}
    for case in dataset:
        for k in required_keys:
            assert k in case and case[k], f"Case {case.get('case_id')} missing required key '{k}'"
        assert isinstance(case["symptoms"], list) and len(case["symptoms"]) > 0

    # Categorize by variant_type
    variants = [c for c in dataset if c["variant_type"] == "paraphrased_variant"]
    decoys = [c for c in dataset if c["variant_type"] == "decoy"]
    novels = [c for c in dataset if c["variant_type"] == "novel"]

    assert len(variants) == 10, f"Expected 10 paraphrased variants, found {len(variants)}"
    assert len(decoys) == 5, f"Expected 5 decoys, found {len(decoys)}"
    assert len(novels) >= 5, f"Expected at least 5 novel cases, found {len(novels)}"

    # Check 5 known families with exactly 2 variants each
    family_variants = {}
    for v in variants:
        fam = v.get("incident_family")
        assert fam is not None, f"Variant {v['case_id']} must specify incident_family"
        family_variants[fam] = family_variants.get(fam, 0) + 1

    assert len(family_variants) == 5, f"Expected 5 distinct families, got {len(family_variants)}"
    for fam, count in family_variants.items():
        assert count == 2, f"Family {fam} has {count} variants, expected 2"

    # Check 1 decoy for each family
    decoy_families = {d.get("incident_family") for d in decoys}
    assert decoy_families == set(family_variants.keys()), "Decoy families must cover all 5 incident families"


def test_variants_have_non_identical_alert_text():
    """Verify variants do not reuse identical alert text or seed incident text."""
    dataset_path = PROJECT_ROOT / "app" / "data" / "eval_dataset.json"
    dataset = load_dataset(dataset_path)

    # Load seed incidents to compare against
    seed_path = PROJECT_ROOT / "app" / "data" / "seed_incidents.json"
    with open(seed_path, "r", encoding="utf-8") as f:
        seeds = json.load(f)

    seed_titles = {s["title"].lower().strip() for s in seeds}
    seed_signatures = {s["alert_signature"].lower().strip() for s in seeds if "alert_signature" in s}

    titles_seen = set()
    variants = [c for c in dataset if c["variant_type"] == "paraphrased_variant"]
    for v in variants:
        title = v["title"].lower().strip()
        assert title not in seed_titles, f"Variant title '{title}' must not be identical to seed incident title"
        assert title not in seed_signatures, f"Variant title '{title}' must not be identical to seed alert signature"
        assert title not in titles_seen, f"Duplicate variant title: {title}"
        titles_seen.add(title)


def test_metrics_calculation_math():
    """Verify calculate_metrics accurately computes rates without inventing fake values."""
    mock_results = [
        # 2 Paraphrased variants for INC-104: both retrieved correctly on Memory ON
        {
            "case_id": "c1",
            "incident_family": "INC-104",
            "variant_type": "paraphrased_variant",
            "memory_enabled": True,
            "historical_match_found": True,
            "recalled_incident_id": "INC-104",
            "match_strength": "High",
            "root_cause": "Timeout",
            "runbook": "RB-1",
            "failed_mitigations": ["restarting"],
            "latency_ms": 10.0,
            "expected_family_retrieved": True,
        },
        {
            "case_id": "c1",
            "incident_family": "INC-104",
            "variant_type": "paraphrased_variant",
            "memory_enabled": False,
            "historical_match_found": False,
            "recalled_incident_id": None,
            "match_strength": "None",
            "root_cause": "Timeout",
            "runbook": None,
            "failed_mitigations": [],
            "latency_ms": 5.0,
            "expected_family_retrieved": False,
        },
        {
            "case_id": "c2",
            "incident_family": "INC-104",
            "variant_type": "paraphrased_variant",
            "memory_enabled": True,
            "historical_match_found": True,
            "recalled_incident_id": "INC-104",
            "match_strength": "High",
            "root_cause": "Timeout",
            "runbook": "RB-1",
            "failed_mitigations": ["restarting"],
            "latency_ms": 12.0,
            "expected_family_retrieved": True,
        },
        {
            "case_id": "c2",
            "incident_family": "INC-104",
            "variant_type": "paraphrased_variant",
            "memory_enabled": False,
            "historical_match_found": False,
            "recalled_incident_id": None,
            "match_strength": "None",
            "root_cause": "Timeout",
            "runbook": None,
            "failed_mitigations": [],
            "latency_ms": 6.0,
            "expected_family_retrieved": False,
        },
        # 1 Decoy: No historical match on Memory ON
        {
            "case_id": "d1",
            "incident_family": "INC-104",
            "variant_type": "decoy",
            "memory_enabled": True,
            "historical_match_found": False,
            "recalled_incident_id": None,
            "match_strength": "None",
            "root_cause": "Cert expired",
            "runbook": None,
            "failed_mitigations": [],
            "latency_ms": 8.0,
            "expected_family_retrieved": True,
        },
        {
            "case_id": "d1",
            "incident_family": "INC-104",
            "variant_type": "decoy",
            "memory_enabled": False,
            "historical_match_found": False,
            "recalled_incident_id": None,
            "match_strength": "None",
            "root_cause": "Cert expired",
            "runbook": None,
            "failed_mitigations": [],
            "latency_ms": 4.0,
            "expected_family_retrieved": True,
        },
        # 1 Novel: No historical match on Memory ON
        {
            "case_id": "n1",
            "incident_family": None,
            "variant_type": "novel",
            "memory_enabled": True,
            "historical_match_found": False,
            "recalled_incident_id": None,
            "match_strength": "None",
            "root_cause": "ES yellow",
            "runbook": None,
            "failed_mitigations": [],
            "latency_ms": 9.0,
            "expected_family_retrieved": True,
        },
        {
            "case_id": "n1",
            "incident_family": None,
            "variant_type": "novel",
            "memory_enabled": False,
            "historical_match_found": False,
            "recalled_incident_id": None,
            "match_strength": "None",
            "root_cause": "ES yellow",
            "runbook": None,
            "failed_mitigations": [],
            "latency_ms": 4.5,
            "expected_family_retrieved": True,
        },
    ]

    metrics = calculate_metrics(mock_results)

    assert metrics["relevant_family_retrieval_rate"] == 1.0  # 2/2 = 100%
    assert metrics["false_retrieval_rate_on_decoys"] == 0.0  # 0/1 = 0%
    assert metrics["novel_case_false_match_rate"] == 0.0  # 0/1 = 0%

    mem_on_ev = metrics["evidence_availability"]["memory_on"]
    mem_off_ev = metrics["evidence_availability"]["memory_off"]

    assert mem_on_ev["historical_match_rate"] == 1.0
    assert mem_off_ev["historical_match_rate"] == 0.0
    assert mem_on_ev["verified_runbook_available_rate"] == 1.0
    assert mem_off_ev["verified_runbook_available_rate"] == 0.0


@pytest.mark.asyncio
async def test_evaluate_single_run_structured_schema():
    """Verify evaluate_single_run returns all 12 required structured fields."""
    mock_engine = MagicMock()
    mock_response = TriageResponse(
        incident_summary="Payment gateway timeout",
        likely_root_cause="Stripe upstream timeout",
        supporting_evidence=["Latency > 35s"],
        historical_matches=[
            HistoricalMatch(
                incident_id="INC-104",
                service="payment-api",
                title="Historical Incident INC-104",
                match_strength="High",
                root_cause="Socket timeout",
                verified_runbook="RB-PAYMENT-CIRCUIT-SHED",
                failed_mitigations=["Restarting pods"],
            )
        ],
        recommended_runbook=RunbookRecommendation(
            runbook_id="RB-PAYMENT-CIRCUIT-SHED",
            title="Trip Payment Circuit Breaker",
            justification="Mitigate Stripe gateway latency cascade",
            blast_radius_analysis="Local payment queue isolation",
            actions=[
                RunbookAction(
                    step_number=1,
                    name="Trip Circuit Breaker",
                    command="curl -X POST http://payment-api/circuit/trip",
                    target_component="payment-api",
                    description="Activate circuit breaker",
                )
            ],
        ),
        failed_mitigations_to_avoid=["Restarting pods"],
        reasoning_summary="SRE root cause analysis",
        requires_human_approval=True,
        memory_used=True,
        novelty=False,
    )
    mock_engine.triage = AsyncMock(return_value=mock_response)

    sample_case = {
        "case_id": "eval-inc104-v1",
        "incident_family": "INC-104",
        "variant_type": "paraphrased_variant",
        "service": "payment-api",
        "title": "Stripe Gateway Egress Latency",
        "description": "High latency to Stripe",
        "symptoms": ["Timeout > 35s"],
        "expected_historical_family": "INC-104",
        "expected_runbook": "RB-PAYMENT-CIRCUIT-SHED",
    }

    result = await evaluate_single_run(sample_case, memory_enabled=True, engine=mock_engine)

    expected_keys = [
        "case_id",
        "incident_family",
        "variant_type",
        "memory_enabled",
        "historical_match_found",
        "recalled_incident_id",
        "match_strength",
        "root_cause",
        "runbook",
        "failed_mitigations",
        "latency_ms",
        "expected_family_retrieved",
    ]

    for k in expected_keys:
        assert k in result, f"Field '{k}' missing from evaluation result"

    assert result["case_id"] == "eval-inc104-v1"
    assert result["incident_family"] == "INC-104"
    assert result["memory_enabled"] is True
    assert result["historical_match_found"] is True
    assert result["recalled_incident_id"] == "INC-104"
    assert result["expected_family_retrieved"] is True
    assert result["runbook"] == "RB-PAYMENT-CIRCUIT-SHED"
    assert len(result["failed_mitigations"]) == 1


def test_markdown_report_formatting():
    """Verify Markdown report generation contains essential sections and tables."""
    mock_metrics = {
        "total_test_cases": 1,
        "total_evaluations": 2,
        "relevant_family_retrieval_rate": 1.0,
        "relevant_family_retrieval_count": "1/1",
        "false_retrieval_rate_on_decoys": 0.0,
        "false_retrieval_count_on_decoys": "0/1",
        "novel_case_false_match_rate": 0.0,
        "novel_case_false_match_count": "0/1",
        "evidence_availability": {
            "memory_on": {
                "total_variant_cases": 1,
                "historical_matches_found": 1,
                "historical_match_rate": 1.0,
                "verified_runbook_available_rate": 1.0,
                "avg_failed_mitigations_documented": 2.0,
                "avg_latency_ms": 14.5,
            },
            "memory_off": {
                "total_variant_cases": 1,
                "historical_matches_found": 0,
                "historical_match_rate": 0.0,
                "verified_runbook_available_rate": 0.0,
                "avg_failed_mitigations_documented": 0.0,
                "avg_latency_ms": 7.2,
            },
        },
    }

    mock_results = [
        {
            "case_id": "eval-inc104-v1",
            "incident_family": "INC-104",
            "variant_type": "paraphrased_variant",
            "memory_enabled": True,
            "historical_match_found": True,
            "recalled_incident_id": "INC-104",
            "match_strength": "High",
            "root_cause": "Gateway timeout",
            "runbook": "RB-PAYMENT-CIRCUIT-SHED",
            "failed_mitigations": ["Pod restarts"],
            "latency_ms": 14.5,
            "expected_family_retrieved": True,
        }
    ]

    report = generate_markdown_report(mock_metrics, mock_results)
    assert "# IncidentOps Copilot — Hindsight Memory Value Evaluation Report" in report
    assert "100.0%" in report
    assert "eval-inc104-v1" in report
    assert "RB-PAYMENT-CIRCUIT-SHED" in report
