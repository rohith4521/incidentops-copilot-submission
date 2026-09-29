"""CLI alert simulator for SRE triage demonstration."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.api.alerts import PRESET_SCENARIOS
from app.models.alert import AlertPayload
from app.models.memory import MatchStrength
from app.services.runbook_service import runbook_service
from app.services.triage_engine import triage_engine


async def run_simulation(scenario_key: str, auto_approve: bool = False):
    print("=" * 72)
    print(" INCIDENTOPS COPILOT — SRE CONTINUOUS MEMORY TRIAGE SIMULATOR")
    print("=" * 72)

    scenario = None
    for s in PRESET_SCENARIOS:
        if scenario_key in s["id"] or scenario_key in s["name"].lower():
            scenario = s
            break

    if not scenario:
        print(f"Unknown scenario '{scenario_key}'. Available options:")
        for s in PRESET_SCENARIOS:
            print(f"  - {s['id']}: {s['name']}")
        return

    print(f"\n[ALERT INGESTION] Triggering scenario: {scenario['name']}")
    print(f"Expected Memory Match: {scenario['expected_match']}")
    alert_dict = scenario["alert"]
    alert = AlertPayload(**alert_dict)

    print(f"Target Service:  {alert.service}")
    print(f"Severity:        {alert.severity.value}")
    print(f"Alert Headline:  {alert.title}")
    print(f"Symptoms:        {', '.join(alert.symptoms)}")

    print("\n[HINDSIGHT MEMORY & GROQ INFERENCE] Executing triage pipeline...")
    result = await triage_engine.execute_triage(alert)

    print("\n" + "=" * 72)
    print(" TRIAGE ASSESSMENT REPORT")
    print("=" * 72)
    print(f"Incident Ref:    {result.incident_id}")
    print(f"Match Strength:  [{result.match_strength.value.upper()}]  <-- Categorical (Truthful Metrics)")
    print(f"Novelty Flag:    {result.novelty_detected}")
    print(f"Inference Model: {result.model_used}")

    print("\n[VERIFIABLE EVIDENCE BULLETS]")
    for bullet in result.evidence_bullets:
        print(f"  * {bullet}")

    print(f"\n[EXECUTIVE TRIAGE SUMMARY]\n{result.triage_summary}")

    print(f"\n[ROOT CAUSE ANALYSIS]")
    print(f"  Hypothesis:           {result.root_cause_analysis.hypothesis}")
    print(f"  Blast Radius:         {result.root_cause_analysis.blast_radius}")
    print(f"  Contributing Factors: {', '.join(result.root_cause_analysis.contributing_factors)}")

    print(f"\n[IMMEDIATE MITIGATION]\n{result.immediate_mitigation}")

    if result.recommended_runbook:
        rb = result.recommended_runbook
        print("\n" + "-" * 72)
        print(f" RECOMMENDED RUNBOOK (HUMAN-IN-THE-LOOP REQUIRED)")
        print("-" * 72)
        print(f"Runbook ID:      {rb.runbook_id}")
        print(f"Title:           {rb.title}")
        print(f"Approval Status: [{rb.status.value}]  <-- Must be APPROVED to simulate")
        print(f"Justification:   {rb.justification}")
        print(f"Blast Radius:    {rb.blast_radius_analysis}")

        print("\nAction Steps:")
        for action in rb.actions:
            print(f"  Step {action.step_number}: {action.name}")
            print(f"    Command: {action.command}")

        # Demonstrate Invariant 4: Attempting simulation before approval will fail
        print("\n[INVARIANT 4 VERIFICATION] Attempting dry-run simulation WITHOUT approval...")
        try:
            runbook_service.simulate_runbook(rb.id, executor="cli-tester")
            print("  UNEXPECTED: Simulation succeeded without approval!")
        except Exception as e:
            print(f"  BLOCKED AS EXPECTED (Invariant 4 Enforced): {e}")

        if auto_approve:
            print("\n[HUMAN APPROVAL] Granting SRE approval for runbook...")
            runbook_service.approve_runbook(rb.id, approver="alice@sre-team.internal", notes="Verified by Lead SRE on call")
            print("  Runbook APPROVED. Re-running simulation harness...")
            sim_res = runbook_service.simulate_runbook(rb.id, executor="alice@sre-team.internal")
            print(f"  Simulation Status: SUCCESS={sim_res.success}")
            for log_line in sim_res.logs[:4]:
                print(f"    {log_line}")
            print("    ...")

    print("\n" + "=" * 72)
    print(" Simulation completed.")
    print("=" * 72)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IncidentOps Copilot Alert Simulator")
    parser.add_argument(
        "--scenario",
        default="redis",
        choices=["redis", "auth", "dns", "novel"],
        help="Alert scenario to trigger (redis, auth, dns, or novel)",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Automatically simulate SRE human approval",
    )
    args = parser.parse_args()
    asyncio.run(run_simulation(args.scenario, auto_approve=args.approve))
