"""PHASE 6.6A — Held-Out Memory Evaluation Tests.

Validates the held-out evaluation framework and deterministic replay curve:
1. Held-out dataset schema and required keys
2. Dataset contains all required scenario categories (>= 15 alerts)
3. Evaluation produces all required metrics with raw counts and percentages
4. Memory ON vs Memory OFF comparison functions correctly
5. Novel alerts do not require or fabricate a known precedent
6. Unverified draft memories are strictly excluded by provenance gate
7. Replay curve demonstrates deterministic continuous knowledge accumulation
"""

import json
from pathlib import Path
import pytest
from typing import Any, Dict, List

from scripts.evaluate_held_out_memory import (
    HeldOutMemoryBank,
    build_default_memory_bank,
    calculate_held_out_metrics,
    evaluate_single_case,
    execute_replay_curve_evaluation,
    run_evaluation,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def held_out_dataset() -> List[Dict[str, Any]]:
    """Load the held-out evaluation dataset."""
    path = PROJECT_ROOT / "app" / "data" / "held_out_evaluation_dataset.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Test 1: Held-Out Dataset Schema
# ---------------------------------------------------------------------------

def test_1_held_out_dataset_schema(held_out_dataset: List[Dict[str, Any]]):
    """Verify that held-out dataset adheres to the required schema."""
    assert len(held_out_dataset) >= 15, f"Expected >= 15 alerts, got {len(held_out_dataset)}"

    required_fields = {
        "case_id",
        "category",
        "service",
        "severity",
        "title",
        "description",
        "symptoms",
        "expected_verdict",
        "expected_match_strength",
    }

    allowed_categories = {"paraphrased_variant", "decoy", "novel", "unverified_memory"}
    case_ids = set()

    for item in held_out_dataset:
        for f in required_fields:
            assert f in item, f"Missing required field '{f}' in item {item.get('case_id')}"

        assert item["category"] in allowed_categories
        assert isinstance(item["symptoms"], list) and len(item["symptoms"]) > 0
        assert item["case_id"] not in case_ids, f"Duplicate case_id: {item['case_id']}"
        case_ids.add(item["case_id"])


# ---------------------------------------------------------------------------
# Test 2: Dataset Contains Required Categories
# ---------------------------------------------------------------------------

def test_2_dataset_contains_required_categories(held_out_dataset: List[Dict[str, Any]]):
    """Ensure dataset includes all 4 required operational categories."""
    categories = {c["category"] for c in held_out_dataset}
    expected_categories = {"paraphrased_variant", "decoy", "novel", "unverified_memory"}
    assert expected_categories.issubset(categories), f"Missing categories: {expected_categories - categories}"

    variants = [c for c in held_out_dataset if c["category"] == "paraphrased_variant"]
    decoys = [c for c in held_out_dataset if c["category"] == "decoy"]
    novels = [c for c in held_out_dataset if c["category"] == "novel"]
    unverified = [c for c in held_out_dataset if c["category"] == "unverified_memory"]

    assert len(variants) >= 5, f"Expected >= 5 paraphrased variants, got {len(variants)}"
    assert len(decoys) >= 5, f"Expected >= 5 decoys, got {len(decoys)}"
    assert len(novels) >= 4, f"Expected >= 4 novel cases, got {len(novels)}"
    assert len(unverified) >= 1, f"Expected >= 1 unverified memory case, got {len(unverified)}"

    # Paraphrased variants must link to known incident families
    for v in variants:
        assert v.get("expected_family"), f"Variant {v['case_id']} missing expected_family"


# ---------------------------------------------------------------------------
# Test 3: Evaluation Produces All Required Metrics
# ---------------------------------------------------------------------------

def test_3_evaluation_produces_all_required_metrics():
    """Verify that evaluation produces all 6 minimum required metrics with raw counts and percentages."""
    metrics, replay_curve, report_md = run_evaluation()

    required_metrics = [
        "relevant_precedent_retrieval",
        "decoy_false_match",
        "decoy_specificity",
        "novel_false_match",
        "unverified_memory_rejection",
        "runbook_grounding",
    ]

    for m in required_metrics:
        assert m in metrics, f"Metrics output missing '{m}'"
        entry = metrics[m]
        assert "rate" in entry and isinstance(entry["rate"], float)
        assert "percentage" in entry and "%" in entry["percentage"]
        assert "count" in entry and "/" in entry["count"]

    # Verify mathematical accuracy of primary rates
    assert metrics["relevant_precedent_retrieval"]["rate"] >= 0.90
    assert metrics["decoy_false_match"]["rate"] <= 0.10
    assert metrics["decoy_specificity"]["rate"] >= 0.90
    assert metrics["novel_false_match"]["rate"] == 0.0
    assert metrics["unverified_memory_rejection"]["rate"] == 1.0
    assert metrics["runbook_grounding"]["rate"] >= 0.90

    # Verify report is populated
    assert "Held-Out Memory Evaluation Report" in report_md
    assert "strictly to this held-out synthetic dataset" in report_md


# ---------------------------------------------------------------------------
# Test 4: Memory ON/OFF Comparison Works
# ---------------------------------------------------------------------------

def test_4_memory_on_off_comparison_works():
    """Verify that Memory ON vs Memory OFF delta is accurately captured."""
    metrics, _, _ = run_evaluation()
    comp = metrics["memory_comparison"]

    assert "memory_on" in comp and "memory_off" in comp
    mem_on = comp["memory_on"]
    mem_off = comp["memory_off"]

    # Memory ON should have high recall and runbook grounding
    assert mem_on["variants_recalled_rate"] >= 0.90
    assert mem_on["runbook_grounding_rate"] >= 0.90
    assert mem_on["avg_failed_mitigations_grounded"] > 0

    # Memory OFF should have zero recall and zero grounding
    assert mem_off["variants_recalled_rate"] == 0.0
    assert mem_off["runbook_grounding_rate"] == 0.0
    assert mem_off["avg_failed_mitigations_grounded"] == 0.0


# ---------------------------------------------------------------------------
# Test 5: Novel Alerts Do Not Require a Known Precedent
# ---------------------------------------------------------------------------

def test_5_novel_alerts_do_not_require_a_known_precedent(held_out_dataset: List[Dict[str, Any]]):
    """Verify novel alerts return no historical match and are flagged as novel."""
    bank = build_default_memory_bank()
    novel_cases = [c for c in held_out_dataset if c["category"] == "novel"]

    assert len(novel_cases) > 0

    for case in novel_cases:
        res = evaluate_single_case(case, bank, enable_memory=True)
        assert res["has_match"] is False, f"Novel case {case['case_id']} unexpectedly matched historical incident"
        assert res["recalled_incident_id"] is None
        assert res["match_strength"] == "None"
        assert res["is_correct"] is True


# ---------------------------------------------------------------------------
# Test 6: Unverified Memories Are Excluded
# ---------------------------------------------------------------------------

def test_6_unverified_memories_are_excluded(held_out_dataset: List[Dict[str, Any]]):
    """Verify unverified draft postmortems are rejected by the provenance gate."""
    bank = build_default_memory_bank()
    unverified_cases = [c for c in held_out_dataset if c["category"] == "unverified_memory"]

    assert len(unverified_cases) > 0

    for case in unverified_cases:
        res = evaluate_single_case(case, bank, enable_memory=True)
        assert res["has_match"] is False, f"Unverified draft unexpectedly matched for {case['case_id']}"
        assert res["recalled_incident_id"] is None
        assert res["relevance_verdict"] == "REJECTED_UNVERIFIED_DRAFT_MEMORY"
        assert res["is_correct"] is True


# ---------------------------------------------------------------------------
# Test 7: Replay Curve Is Deterministic
# ---------------------------------------------------------------------------

def test_7_replay_curve_is_deterministic(held_out_dataset: List[Dict[str, Any]]):
    """Verify incremental replay curve is deterministic and monotonically non-decreasing."""
    curve_1 = execute_replay_curve_evaluation(held_out_dataset)
    curve_2 = execute_replay_curve_evaluation(held_out_dataset)

    # Identical runs produce identical results
    assert curve_1 == curve_2

    steps = curve_1["steps"]
    assert len(steps) == 6  # Step 0 (base) + 5 incident ingestion steps

    # Step 0: 0 incidents in memory -> 0 recall
    assert steps[0]["verified_memories_count"] == 0
    assert steps[0]["recalled_count"] == 0
    assert steps[0]["recall_rate"] == 0.0

    # Step 5: 5 verified incidents in memory -> 100% recall
    assert steps[-1]["verified_memories_count"] == 5
    assert steps[-1]["recalled_count"] == 5
    assert steps[-1]["recall_rate"] == 1.0

    # Monotonic accumulation: every step retains or improves recall
    assert curve_1["is_monotonically_non_decreasing"] is True

    # Check incremental progression
    expected_rates = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    actual_rates = [s["recall_rate"] for s in steps]
    assert actual_rates == expected_rates
