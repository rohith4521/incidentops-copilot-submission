"""Triage Orchestration Engine.

Orchestrates the continuous memory triage loop:
Alert Ingestion -> Hindsight Memory Recall -> Truthful Categorization ->
Groq SRE Inference -> Human-in-the-Loop Runbook Registration -> Triage Report.
"""

import logging
from typing import Optional
from app.models.alert import AlertPayload, AlertSeverity
from app.models.memory import MatchStrength, RecallResultSummary
from app.models.triage import TriageRequest, TriageResponse, TriageResult
from app.services.groq_service import groq_service
from app.services.hindsight_service import hindsight_service
from app.services.runbook_service import runbook_service

logger = logging.getLogger("incidentops.engine")


class TriageOrchestrationEngine:
    """End-to-end incident triage coordinator."""

    def __init__(self):
        self.hindsight = hindsight_service
        self.groq = groq_service
        self.runbooks = runbook_service

    async def triage(self, request: TriageRequest) -> TriageResponse:
        """Run production-quality incident triage pipeline on TriageRequest (Phase 2)."""
        from app.services.metrics_service import metrics_service
        metrics_service.inc_triage_requests()

        logger.info(
            "Initiating triage for service '%s', alert '%s' (enable_memory=%s)...",
            request.service,
            request.alert_title,
            request.enable_memory,
        )

        recall_summary: Optional[RecallResultSummary] = None

        try:
            if request.enable_memory:
                # Step 1: Query the REAL existing Hindsight service
                # Build normalized AlertPayload for recall
                sev = AlertSeverity.HIGH
                try:
                    sev = AlertSeverity(request.severity.upper())
                except Exception:
                    sev = AlertSeverity.HIGH

                from app.services.security_service import security_service
                clean_title, _ = security_service.defuse_untrusted_text(request.alert_title, field_name="alert_title")
                clean_desc, _ = security_service.defuse_untrusted_text(
                    request.description or f"Operational alert {request.alert_title} for service {request.service}.",
                    field_name="description",
                )
                clean_symptoms = [
                    security_service.defuse_untrusted_text(s, field_name="symptom")[0]
                    for s in request.normalized_symptoms
                ]

                alert_payload = AlertPayload(
                    title=clean_title,
                    service=request.service,
                    severity=sev,
                    description=clean_desc,
                    symptoms=clean_symptoms,
                    metrics=request.context if isinstance(request.context, dict) else {},
                )

                try:
                    recall_summary = await self.hindsight.recall_incident_memory(alert_payload)
                except Exception as e:
                    logger.error("Hindsight recall error: %s. Continuing with degraded memory.", e)
                    is_cb_open = bool(
                        getattr(getattr(self.hindsight, "circuit_breaker", None), "is_open", False)
                        or "circuit_open" in str(e).lower()
                    )
                    recall_summary = RecallResultSummary(
                        match_strength=MatchStrength.NONE,
                        is_novel=True,
                        memories_found=[],
                        evidence_bullets=[
                            "Hindsight circuit breaker is OPEN; operating statelessly." if is_cb_open
                            else f"Hindsight query failed: {str(e)}. Operating in first-principles mode."
                        ],
                        query_used=request.alert_title,
                        hindsight_connected=False,
                        diagnostic_note="hindsight_circuit_open" if is_cb_open else f"Hindsight recall error: {str(e)}",
                    )

            # Step 2: Groq SRE Incident Commander reasoning / fallback core triage
            response = await self.groq.triage_core(
                request=request,
                recall_summary=recall_summary,
                enable_memory=request.enable_memory,
                override_model=request.model,
            )

            if getattr(response, "degraded", False):
                metrics_service.inc_degraded_triage_count()

            # Step 3: Register recommended runbook into Human-in-the-Loop registry
            if response.recommended_runbook:
                self.runbooks.register_recommendation(response.recommended_runbook)

            logger.info(
                "Triage completed for '%s'. Memory used: %s, Novelty: %s, Requires approval: %s",
                request.service,
                response.memory_used,
                response.novelty,
                response.requires_human_approval,
            )
            return response
        except Exception:
            metrics_service.inc_triage_failures()
            raise

    async def execute_triage(
        self,
        alert: AlertPayload,
        override_model: Optional[str] = None,
    ) -> TriageResult:
        """Run complete incident triage pipeline on an operational alert (Legacy compatibility)."""
        from app.services.metrics_service import metrics_service
        metrics_service.inc_triage_requests()

        try:
            logger.info("Initiating triage for alert '%s' (%s, %s)...", alert.id, alert.service, alert.severity.value)

            # Step 1: Genuine Hindsight Memory Recall
            recall_summary = await self.hindsight.recall_incident_memory(alert)

            # Step 2: Groq SRE Incident Commander reasoning
            triage_result = await self.groq.triage_alert(
                alert=alert,
                recall_summary=recall_summary,
                override_model=override_model,
            )

            # Step 3: Register recommended runbook into Human-in-the-Loop registry
            if triage_result.recommended_runbook:
                self.runbooks.register_recommendation(triage_result.recommended_runbook)

            logger.info(
                "Triage completed for alert '%s'. Match strength: '%s', Novel: %s",
                alert.id,
                triage_result.match_strength.value,
                triage_result.novelty_detected,
            )
            return triage_result
        except Exception:
            metrics_service.inc_triage_failures()
            raise


# Global singleton instance
triage_engine = TriageOrchestrationEngine()
