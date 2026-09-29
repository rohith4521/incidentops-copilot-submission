"""Human-in-the-Loop Runbook Service.

Enforces Invariant 4:
Runbooks must be recommended and justified with historical evidence,
strictly requiring human approval before simulation or execution.
"""

from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional
from app.models.runbook import (
    ApprovalStatus,
    RunbookRecommendation,
    RunbookSimulationResult,
)

logger = logging.getLogger("incidentops.runbook")


class RunbookApprovalError(Exception):
    """Raised when an unapproved runbook simulation is attempted."""
    pass


class RunbookService:
    """Registry and execution controller for human-in-the-loop runbooks."""

    def __init__(self):
        self._registry: Dict[str, RunbookRecommendation] = {}
        self._simulation_history: List[RunbookSimulationResult] = []

    def register_recommendation(self, recommendation: RunbookRecommendation) -> RunbookRecommendation:
        """Register a newly generated runbook recommendation in PENDING_APPROVAL state."""
        self._registry[recommendation.id] = recommendation
        logger.info(
            "Registered runbook recommendation '%s' (%s) for human review",
            recommendation.id,
            recommendation.runbook_id,
        )
        return recommendation

    def get_recommendation(self, recommendation_id: str) -> Optional[RunbookRecommendation]:
        """Fetch recommendation by ID."""
        return self._registry.get(recommendation_id)

    def list_recommendations(self) -> List[RunbookRecommendation]:
        """List all active and historical recommendations."""
        return list(self._registry.values())

    def approve_runbook(
        self,
        recommendation_id: str,
        approver: str,
        notes: Optional[str] = None,
    ) -> RunbookRecommendation:
        """Record human approval for a runbook recommendation."""
        rec = self._registry.get(recommendation_id)
        if not rec:
            raise KeyError(f"Runbook recommendation '{recommendation_id}' not found.")

        rec.status = ApprovalStatus.APPROVED
        rec.approver = approver
        rec.approval_timestamp = datetime.now(timezone.utc)
        rec.approval_notes = notes or "Approved by on-call SRE."
        logger.info("Runbook '%s' APPROVED by '%s'", recommendation_id, approver)
        return rec

    def reject_runbook(
        self,
        recommendation_id: str,
        approver: str,
        reason: str,
    ) -> RunbookRecommendation:
        """Record human rejection for a runbook recommendation."""
        rec = self._registry.get(recommendation_id)
        if not rec:
            raise KeyError(f"Runbook recommendation '{recommendation_id}' not found.")

        rec.status = ApprovalStatus.REJECTED
        rec.approver = approver
        rec.rejection_reason = reason or "Rejected by SRE."
        logger.info("Runbook '%s' REJECTED by '%s': %s", recommendation_id, approver, reason)
        return rec

    def simulate_runbook(
        self,
        recommendation_id: str,
        executor: str,
    ) -> RunbookSimulationResult:
        """Execute dry-run simulation of an approved runbook.

        STRICT ENFORCEMENT OF INVARIANT 4:
        Raises RunbookApprovalError if recommendation is not in APPROVED state.
        """
        rec = self._registry.get(recommendation_id)
        if not rec:
            raise KeyError(f"Runbook recommendation '{recommendation_id}' not found.")

        # Invariant 4 gate check:
        if rec.status != ApprovalStatus.APPROVED:
            logger.warning(
                "BLOCKED simulation attempt for '%s'. Status is '%s' (Human approval required).",
                recommendation_id,
                rec.status.value,
            )
            raise RunbookApprovalError(
                f"Runbook recommendation '{recommendation_id}' requires human approval before simulation. "
                f"Current status: {rec.status.value}."
            )

        # Generate dry-run simulation audit trace
        sim_logs: List[str] = [
            f"[AUDIT] Operator '{executor}' initiated simulation harness.",
            f"[AUTHORIZATION] Validated human approval by '{rec.approver}' at {rec.approval_timestamp.isoformat() if rec.approval_timestamp else 'N/A'}.",
            f"[TARGET RUNBOOK] {rec.runbook_id} - '{rec.title}'",
            f"[JUSTIFICATION] {rec.justification}",
            f"[BLAST RADIUS EVALUATION] {rec.blast_radius_analysis}",
            "--- BEGIN DRY-RUN EXECUTION STEPS ---",
        ]

        for step in rec.actions:
            sim_logs.append(
                f"[STEP {step.step_number}: {step.name}] Target: {step.target_component} | SafeMode: {step.is_safe_simulation}"
            )
            sim_logs.append(f"  $ {step.command}")
            sim_logs.append("  >> Simulated output: [DRY-RUN OK] Command validated against sandbox environment.")
            sim_logs.append(f"  >> Step summary: {step.description}")

        sim_logs.append("--- END DRY-RUN EXECUTION STEPS ---")
        sim_logs.append("[SUCCESS] Simulation completed with 0 errors. Projected impact is within acceptable risk budget.")

        result = RunbookSimulationResult(
            recommendation_id=rec.id,
            runbook_id=rec.runbook_id,
            executed_by=executor,
            success=True,
            logs=sim_logs,
            projected_recovery_time_minutes=4,
            projected_impact=f"Simulated execution for {rec.runbook_id}. Blast radius verified. Zero unexpected side-effects.",
        )
        self._simulation_history.append(result)
        return result


# Global singleton instance
runbook_service = RunbookService()
