"""Diagnosis Quality Benchmark Service (Phase 7.5).

Measures whether trusted Hindsight continuous memory improves root-cause diagnosis quality
and runbook recommendation accuracy compared with stateless first-principles triage.

Enforces:
1. Ground truth isolation: Evaluation-only fields never enter the triage request or LLM prompt.
2. Exact comparable conditions: Memory OFF vs Memory ON with identical alert inputs.
3. Deterministic scoring rules: Normalized alias/failure-domain matching without non-deterministic LLM judges.
4. Clear separation of metrics:
   - Retrieval correctness
   - Evidence correctness
   - Diagnosis correctness
5. Truthful reporting: Measures actual differences and false-grounding rates without manufactured numbers.
"""

from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from app.models.triage import TriageRequest, TriageResponse
from app.services.triage_engine import triage_engine

logger = logging.getLogger("incidentops.benchmark")
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class ConditionScore:
    """Scoring result for a single scenario under a specific memory condition."""
    condition: str  # "MEMORY_OFF" or "MEMORY_ON"
    diagnosis_correct: bool
    runbook_correct: bool
    retrieval_correct: bool
    precedent_used: bool
    false_historical_grounding: bool
    novel_false_grounding: bool
    evidence_correct: bool
    likely_root_cause: str
    recommended_runbook_id: Optional[str]
    matched_incident_ids: List[str]


@dataclass
class ScenarioBenchmarkScore:
    """Paired evaluation result for a benchmark scenario under both Memory OFF and Memory ON."""
    scenario_id: str
    category: str
    service: str
    title: str
    failure_domain: str
    has_trusted_precedent: bool
    expected_root_cause_family: str
    expected_runbook_family: str
    expected_precedent_id: Optional[str]
    off: ConditionScore
    on: ConditionScore


@dataclass
class BenchmarkSummary:
    """Aggregated diagnosis quality benchmark metrics and category breakdowns."""
    dataset_size: int
    root_cause_accuracy_off: float
    root_cause_accuracy_on: float
    runbook_accuracy_off: float
    runbook_accuracy_on: float
    absolute_root_cause_improvement: float
    absolute_runbook_improvement: float
    false_historical_grounding_rate_off: float
    false_historical_grounding_rate_on: float
    novel_false_grounding_rate_off: float
    novel_false_grounding_rate_on: float
    retrieval_correctness_rate_on: float
    evidence_correctness_rate_on: float
    category_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    scenarios: List[ScenarioBenchmarkScore] = field(default_factory=list)


def load_benchmark_dataset(dataset_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load the held-out diagnosis quality benchmark dataset."""
    path = Path(dataset_path) if dataset_path else PROJECT_ROOT / "app" / "data" / "diagnosis_quality_dataset.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_isolated_triage_request(
    scenario: Dict[str, Any],
    enable_memory: bool,
) -> TriageRequest:
    """Build an operational TriageRequest isolating all evaluation-only ground truth fields.

    Prevents benchmark leakage: Only operational telemetry is passed.
    Evaluation fields (expected_root_cause_family, acceptable_aliases, etc.) are strictly excluded.
    """
    return TriageRequest(
        service=scenario["service"],
        alert=scenario.get("title") or scenario.get("alert"),
        description=scenario.get("description"),
        symptoms=scenario.get("symptoms", []),
        severity=scenario.get("severity", "HIGH"),
        context=scenario.get("context"),
        enable_memory=enable_memory,
    )


def score_single_condition(
    scenario: Dict[str, Any],
    response: TriageResponse,
    condition: str,
) -> ConditionScore:
    """Deterministically score a triage response against the scenario's ground-truth criteria."""
    has_precedent = scenario.get("has_trusted_precedent", False)
    expected_precedent_id = scenario.get("expected_precedent_id")
    category = scenario.get("category", "novel")

    matched_ids = list(dict.fromkeys([
        str(m.incident_id).strip().upper()
        for m in getattr(response, "historical_matches", [])
        if getattr(m, "incident_id", None)
    ]))

    # 1. Diagnosis Correctness (Normalized root cause family & aliases check with word boundaries)
    likely_rc = (response.likely_root_cause or "").lower()
    summary = (response.incident_summary or "").lower()
    reasoning = (response.reasoning_summary or "").lower()
    combined_diag_text = re.sub(r"[-_]", " ", f"{likely_rc} {summary} {reasoning}")

    expected_family = str(scenario.get("expected_root_cause_family", "")).lower()
    acceptable_aliases = [
        str(a).lower().strip()
        for a in scenario.get("acceptable_root_cause_aliases", [])
        if str(a).strip()
    ]

    def _matches_phrase(phrase: str, text: str) -> bool:
        norm_p = re.sub(r"[-_]", " ", phrase).strip()
        if not norm_p:
            return False
        words = norm_p.split()
        pattern = r"\b" + r"\s+".join(re.escape(w) for w in words) + r"\b"
        return bool(re.search(pattern, text))

    diagnosis_correct = False
    if expected_family and _matches_phrase(expected_family, combined_diag_text):
        diagnosis_correct = True
    elif any(_matches_phrase(alias, combined_diag_text) for alias in acceptable_aliases):
        diagnosis_correct = True

    # 2. Runbook Family Accuracy
    recommended_rb = response.recommended_runbook
    actual_rb_id = (recommended_rb.runbook_id or "").upper().strip() if recommended_rb else ""
    actual_rb_title = (recommended_rb.title or "").lower() if recommended_rb else ""

    expected_rb_family = str(scenario.get("expected_runbook_family", "")).upper().strip()
    acceptable_rb_aliases = [
        str(a).lower().strip()
        for a in scenario.get("acceptable_runbook_aliases", [])
        if str(a).strip()
    ]

    runbook_correct = False
    if expected_rb_family and (expected_rb_family in actual_rb_id or expected_rb_family.replace("-", " ") in actual_rb_id.replace("-", " ")):
        runbook_correct = True
    else:
        actual_rb_norm = re.sub(r"[-_]", " ", actual_rb_id.lower())
        title_norm = re.sub(r"[-_]", " ", actual_rb_title)
        combined_rb_text = f"{actual_rb_norm} {title_norm}"
        for alias in acceptable_rb_aliases:
            alias_norm = re.sub(r"[-_]", " ", alias)
            if alias in actual_rb_id.lower() or alias_norm in combined_rb_text:
                runbook_correct = True
                break
            alias_tokens = alias_norm.split()
            if alias_tokens and all(tok in combined_rb_text for tok in alias_tokens):
                runbook_correct = True
                break

    # 3. Retrieval Correctness
    if has_precedent and expected_precedent_id:
        retrieval_correct = expected_precedent_id.upper() in matched_ids
    else:
        # For decoys and novel alerts, retrieval is correct IF no historical matches were accepted
        retrieval_correct = len(matched_ids) == 0

    # 4. Correct Trusted Precedent Usage
    if has_precedent and expected_precedent_id:
        rb_ref = (recommended_rb.historical_reference_id or "").upper() if recommended_rb else ""
        precedent_used = expected_precedent_id.upper() in matched_ids or expected_precedent_id.upper() == rb_ref
    else:
        precedent_used = False

    # 5. False Historical Grounding (Claiming historical match when none exists)
    if not has_precedent:
        rb_ref = (recommended_rb.historical_reference_id or "").strip() if recommended_rb else ""
        false_historical_grounding = bool(matched_ids or (rb_ref and rb_ref.lower() != "none"))
    else:
        false_historical_grounding = False

    # 6. Novel-Incident False Grounding (Specifically for novel category)
    if category == "novel":
        novel_false_grounding = bool(matched_ids or not response.novelty)
    else:
        novel_false_grounding = False

    # 7. Evidence Correctness (Factual evidence without ungrounded postmortems)
    if has_precedent and condition == "MEMORY_ON":
        evidence_correct = bool(
            response.supporting_evidence
            and not response.novelty
            and (not matched_ids or (expected_precedent_id is not None and expected_precedent_id.upper() in matched_ids))
        )
    elif condition == "MEMORY_OFF":
        evidence_correct = bool(response.novelty and not response.historical_matches)
    else:
        # Decoys / Novel under memory: must not fabricate historical matches and must preserve novelty
        evidence_correct = bool(not response.historical_matches and response.novelty)

    return ConditionScore(
        condition=condition,
        diagnosis_correct=diagnosis_correct,
        runbook_correct=runbook_correct,
        retrieval_correct=retrieval_correct,
        precedent_used=precedent_used,
        false_historical_grounding=false_historical_grounding,
        novel_false_grounding=novel_false_grounding,
        evidence_correct=evidence_correct,
        likely_root_cause=response.likely_root_cause or "",
        recommended_runbook_id=actual_rb_id or None,
        matched_incident_ids=matched_ids,
    )


class DiagnosisQualityBenchmark:
    """Benchmark runner evaluating SRE diagnosis quality under Memory OFF vs Memory ON."""

    def __init__(self, engine=triage_engine, dataset: Optional[List[Dict[str, Any]]] = None):
        self.engine = engine
        self.dataset = dataset or load_benchmark_dataset()

    async def evaluate_scenario(self, scenario: Dict[str, Any]) -> ScenarioBenchmarkScore:
        """Run and score both Memory OFF and Memory ON conditions for a scenario."""
        # Condition A: Memory OFF
        req_off = build_isolated_triage_request(scenario, enable_memory=False)
        resp_off = await self.engine.triage(req_off)
        score_off = score_single_condition(scenario, resp_off, condition="MEMORY_OFF")

        # Condition B: Memory ON
        req_on = build_isolated_triage_request(scenario, enable_memory=True)
        resp_on = await self.engine.triage(req_on)
        score_on = score_single_condition(scenario, resp_on, condition="MEMORY_ON")

        return ScenarioBenchmarkScore(
            scenario_id=scenario["scenario_id"],
            category=scenario["category"],
            service=scenario["service"],
            title=scenario.get("title", ""),
            failure_domain=scenario.get("failure_domain", ""),
            has_trusted_precedent=scenario.get("has_trusted_precedent", False),
            expected_root_cause_family=scenario.get("expected_root_cause_family", ""),
            expected_runbook_family=scenario.get("expected_runbook_family", ""),
            expected_precedent_id=scenario.get("expected_precedent_id"),
            off=score_off,
            on=score_on,
        )

    async def run_benchmark(self) -> BenchmarkSummary:
        """Execute the full benchmark suite across all scenarios and compute aggregate metrics."""
        results: List[ScenarioBenchmarkScore] = []

        for scenario in self.dataset:
            result = await self.evaluate_scenario(scenario)
            results.append(result)

        total = len(results)
        if total == 0:
            return BenchmarkSummary(
                dataset_size=0,
                root_cause_accuracy_off=0.0,
                root_cause_accuracy_on=0.0,
                runbook_accuracy_off=0.0,
                runbook_accuracy_on=0.0,
                absolute_root_cause_improvement=0.0,
                absolute_runbook_improvement=0.0,
                false_historical_grounding_rate_off=0.0,
                false_historical_grounding_rate_on=0.0,
                novel_false_grounding_rate_off=0.0,
                novel_false_grounding_rate_on=0.0,
                retrieval_correctness_rate_on=0.0,
                evidence_correctness_rate_on=0.0,
                category_breakdown={},
                scenarios=[],
            )

        # Aggregate accuracies
        diag_off_count = sum(1 for r in results if r.off.diagnosis_correct)
        diag_on_count = sum(1 for r in results if r.on.diagnosis_correct)
        rb_off_count = sum(1 for r in results if r.off.runbook_correct)
        rb_on_count = sum(1 for r in results if r.on.runbook_correct)

        diag_acc_off = round((diag_off_count / total) * 100, 2)
        diag_acc_on = round((diag_on_count / total) * 100, 2)
        rb_acc_off = round((rb_off_count / total) * 100, 2)
        rb_acc_on = round((rb_on_count / total) * 100, 2)

        # False historical grounding on non-precedent scenarios (decoys + novel)
        non_precedent = [r for r in results if not r.has_trusted_precedent]
        np_total = len(non_precedent) or 1
        false_grounding_off = round((sum(1 for r in non_precedent if r.off.false_historical_grounding) / np_total) * 100, 2)
        false_grounding_on = round((sum(1 for r in non_precedent if r.on.false_historical_grounding) / np_total) * 100, 2)

        # Novel false grounding on novel scenarios
        novel_cases = [r for r in results if r.category == "novel"]
        nov_total = len(novel_cases) or 1
        nov_false_grounding_off = round((sum(1 for r in novel_cases if r.off.novel_false_grounding) / nov_total) * 100, 2)
        nov_false_grounding_on = round((sum(1 for r in novel_cases if r.on.novel_false_grounding) / nov_total) * 100, 2)

        # Retrieval and evidence correctness on Memory ON
        retrieval_correct_on = round((sum(1 for r in results if r.on.retrieval_correct) / total) * 100, 2)
        evidence_correct_on = round((sum(1 for r in results if r.on.evidence_correct) / total) * 100, 2)

        # Category breakdown
        categories = ["known", "paraphrased", "decoy", "novel"]
        breakdown: Dict[str, Dict[str, Any]] = {}
        for cat in categories:
            cat_items = [r for r in results if r.category == cat]
            c_tot = len(cat_items)
            if c_tot == 0:
                continue
            c_diag_off = sum(1 for r in cat_items if r.off.diagnosis_correct)
            c_diag_on = sum(1 for r in cat_items if r.on.diagnosis_correct)
            c_rb_off = sum(1 for r in cat_items if r.off.runbook_correct)
            c_rb_on = sum(1 for r in cat_items if r.on.runbook_correct)
            breakdown[cat] = {
                "count": c_tot,
                "diag_accuracy_off": round((c_diag_off / c_tot) * 100, 1),
                "diag_accuracy_on": round((c_diag_on / c_tot) * 100, 1),
                "diag_improvement": round(((c_diag_on - c_diag_off) / c_tot) * 100, 1),
                "runbook_accuracy_off": round((c_rb_off / c_tot) * 100, 1),
                "runbook_accuracy_on": round((c_rb_on / c_tot) * 100, 1),
                "runbook_improvement": round(((c_rb_on - c_rb_off) / c_tot) * 100, 1),
            }

        return BenchmarkSummary(
            dataset_size=total,
            root_cause_accuracy_off=diag_acc_off,
            root_cause_accuracy_on=diag_acc_on,
            runbook_accuracy_off=rb_acc_off,
            runbook_accuracy_on=rb_acc_on,
            absolute_root_cause_improvement=round(diag_acc_on - diag_acc_off, 2),
            absolute_runbook_improvement=round(rb_acc_on - rb_acc_off, 2),
            false_historical_grounding_rate_off=false_grounding_off,
            false_historical_grounding_rate_on=false_grounding_on,
            novel_false_grounding_rate_off=nov_false_grounding_off,
            novel_false_grounding_rate_on=nov_false_grounding_on,
            retrieval_correctness_rate_on=retrieval_correct_on,
            evidence_correctness_rate_on=evidence_correct_on,
            category_breakdown=breakdown,
            scenarios=results,
        )


diagnosis_benchmark = DiagnosisQualityBenchmark()
