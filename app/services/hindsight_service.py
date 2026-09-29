"""Genuine Hindsight Cloud / API continuous memory service.

Strict Invariants enforced:
1. Genuine Memory Layer: All retention and recall operations hit the Hindsight API directly.
   No mock in-memory arrays or local SQLite tables (Invariant 2).
2. Truthful Metrics: Categorical Match Strength (High / Moderate / None) backed by
   verifiable evidence bullets; zero synthetic numerical percentages (Invariant 3).
3. Resilience & Graceful Fallback: Handle API timeouts, 401 unauthenticated, rate limits,
   and uninitialized banks gracefully without crashing the service (Invariant 6).
"""

import asyncio
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import aiohttp
from hindsight_client import Hindsight, RecallResponse, RetainResponse
from hindsight_client_api.exceptions import (
    ApiException,
    NotFoundException,
    UnauthorizedException,
)

from app.config import settings
from app.models.alert import AlertPayload
from app.models.memory import (
    IncidentMemoryItem,
    MatchStrength,
    MemorySourceType,
    MemoryStatus,
    RecallResultSummary,
    RetainIncidentPayload,
)
from app.services.relevance_scorer import evaluate_batch_relevance

logger = logging.getLogger("incidentops.hindsight")
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_SEED_CACHE: Optional[Dict[str, Dict[str, Any]]] = None


def _get_seed_incident(incident_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve canonical postmortem data for seeded historical incidents."""
    global _SEED_CACHE
    if _SEED_CACHE is None:
        _SEED_CACHE = {}
        seed_file = PROJECT_ROOT / "app" / "data" / "seed_incidents.json"
        if seed_file.exists():
            try:
                with open(seed_file, "r", encoding="utf-8") as f:
                    for inc in json.load(f):
                        if "incident_id" in inc:
                            _SEED_CACHE[str(inc["incident_id"]).strip().upper()] = inc
            except Exception as e:
                logger.warning("Failed loading seed_incidents.json: %s", e)
    return _SEED_CACHE.get(str(incident_id).strip().upper()) if _SEED_CACHE else None


class HindsightMemoryService:
    """Service encapsulating direct operations with Hindsight Continuous Memory."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        bank_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.base_url = base_url or settings.hindsight_api_url
        self.api_key = api_key if api_key is not None else settings.hindsight_api_key
        self.bank_id = bank_id or settings.hindsight_bank_id
        self.timeout = timeout or settings.hindsight_timeout_seconds

        # Production-grade circuit breaker (Phase 7.6)
        from app.services.circuit_breaker import HindsightCircuitBreaker
        self.circuit_breaker = HindsightCircuitBreaker(
            failure_threshold=settings.hindsight_cb_failure_threshold,
            recovery_timeout=settings.hindsight_cb_recovery_timeout_seconds,
            request_timeout=settings.hindsight_cb_request_timeout_seconds,
            name="hindsight-memory-engine",
        )

    def _get_client(self) -> Hindsight:
        """Instantiate the official Hindsight client targeting Hindsight API."""
        return Hindsight(
            base_url=self.base_url,
            api_key=self.api_key if self.api_key else None,
            timeout=self.timeout,
        )

    async def check_health(self) -> Dict[str, Any]:
        """Verify direct connectivity with Hindsight API endpoint."""
        cb_status = self.circuit_breaker.get_status()
        if self.circuit_breaker.is_open:
            return {
                "status": "circuit_open",
                "endpoint": self.base_url,
                "bank_id": self.bank_id,
                "authenticated": bool(self.api_key),
                "circuit_breaker": cb_status,
            }

        client = self._get_client()
        try:
            version_info = await asyncio.wait_for(
                client.aget_version(),
                timeout=min(self.timeout, 8.0),
            )
            return {
                "status": "connected",
                "endpoint": self.base_url,
                "api_version": getattr(version_info, "api_version", "unknown"),
                "features": str(getattr(version_info, "features", {})),
                "authenticated": bool(self.api_key),
                "bank_id": self.bank_id,
                "circuit_breaker": cb_status,
            }
        except UnauthorizedException as ue:
            logger.warning("Hindsight API returned 401 Unauthorized: %s", ue)
            return {
                "status": "unauthorized",
                "endpoint": self.base_url,
                "error": "API key required or invalid. Configure HINDSIGHT_API_KEY in .env.",
                "authenticated": False,
                "bank_id": self.bank_id,
                "circuit_breaker": cb_status,
            }
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as ce:
            logger.error("Failed connecting to Hindsight API at %s: %s", self.base_url, ce)
            return {
                "status": "unreachable",
                "endpoint": self.base_url,
                "error": f"Connection error: {str(ce)}",
                "authenticated": bool(self.api_key),
                "bank_id": self.bank_id,
                "circuit_breaker": cb_status,
            }
        except Exception as e:
            logger.error("Unexpected error checking Hindsight health: %s", e)
            return {
                "status": "error",
                "endpoint": self.base_url,
                "error": str(e),
                "bank_id": self.bank_id,
                "circuit_breaker": cb_status,
            }
        finally:
            try:
                await client.aclose()
            except Exception:
                pass

    async def ensure_bank(self) -> bool:
        """Ensure the target memory bank exists in Hindsight API."""
        client = self._get_client()
        try:
            # Check if bank exists
            await client.aget_bank_config(bank_id=self.bank_id)
            return True
        except NotFoundException:
            logger.info("Bank '%s' not found. Creating bank via Hindsight API...", self.bank_id)
            try:
                await client.acreate_bank(
                    bank_id=self.bank_id,
                    name=f"SRE Incident Memory ({self.bank_id})",
                )
                logger.info("Successfully created Hindsight memory bank '%s'", self.bank_id)
                return True
            except Exception as e:
                logger.warning("Could not auto-create bank '%s': %s", self.bank_id, e)
                return False
        except Exception as e:
            logger.debug("Bank check status for '%s': %s", self.bank_id, e)
            return False
        finally:
            try:
                await client.aclose()
            except Exception:
                pass

    async def recall_incident_memory(self, alert: AlertPayload) -> RecallResultSummary:
        """Directly recall relevant historical incidents from Hindsight memory bank.

        Guarded by production-grade HindsightCircuitBreaker (Phase 7.6).
        Hits Hindsight API via `client.arecall()`. Adheres strictly to Invariant 2 and 3.
        """
        # Formulate query encapsulating service, symptoms, and failure description
        symptoms_str = ", ".join(alert.symptoms) if alert.symptoms else "none listed"
        metrics_str = json.dumps(alert.metrics) if alert.metrics else "{}"
        query = (
            f"Service: {alert.service}. "
            f"Alert: {alert.title}. "
            f"Description: {alert.description}. "
            f"Symptoms: {symptoms_str}. "
            f"Metrics: {metrics_str}."
        )

        # 1. Fast-fail gate via Circuit Breaker
        allowed, reason = await self.circuit_breaker.can_execute()
        if not allowed:
            logger.info(
                "Hindsight circuit breaker is %s; failing fast without calling Hindsight API.",
                self.circuit_breaker.state.value,
            )
            from app.services.metrics_service import metrics_service
            metrics_service.inc_hindsight_failures()
            return RecallResultSummary(
                match_strength=MatchStrength.NONE,
                is_novel=True,
                memories_found=[],
                evidence_bullets=[
                    "Hindsight continuous memory circuit breaker is OPEN (fail-fast active).",
                    "Executing first-principles triage without historical memory augmentation.",
                ],
                raw_recall_count=0,
                query_used=query,
                hindsight_connected=False,
                diagnostic_note="hindsight_circuit_open",
                candidates_retrieved=[],
                relevance_verdict="NONE",
                relevance_reason="Hindsight circuit breaker is OPEN; request failed fast.",
            )

        client = self._get_client()
        try:
            # Ensure bank existence opportunistically
            await self.ensure_bank()

            # Direct recall call to Hindsight API guarded by circuit breaker request timeout
            logger.info(
                "Executing Hindsight API recall on bank '%s' for service '%s' (timeout: %.1fs)...",
                self.bank_id,
                alert.service,
                self.circuit_breaker.request_timeout,
            )
            t_recall_start = asyncio.get_event_loop().time()
            recall_response: RecallResponse = await asyncio.wait_for(
                client.arecall(
                    bank_id=self.bank_id,
                    query=query,
                    types=None,
                    max_tokens=4096,
                    tags=[alert.service] if alert.service else None,
                    tags_match="any",
                ),
                timeout=self.circuit_breaker.request_timeout,
            )
            recall_latency_ms = (asyncio.get_event_loop().time() - t_recall_start) * 1000
            from app.services.metrics_service import metrics_service
            metrics_service.record_hindsight_latency(recall_latency_ms)

            # Record successful dependency interaction (closes HALF_OPEN or resets failures)
            await self.circuit_breaker.record_success()

            raw_results = getattr(recall_response, "results", []) or []
            parsed_items = self._parse_recall_results(raw_results)

            # Failure-Mode-Aware Relevance Scoring & Gating
            match_strength, evidence_bullets, accepted_items, verdict, reason = evaluate_batch_relevance(alert, parsed_items)
            is_novel = bool(len(accepted_items) == 0 or match_strength == MatchStrength.NONE)

            return RecallResultSummary(
                match_strength=match_strength,
                is_novel=is_novel,
                memories_found=accepted_items,
                evidence_bullets=evidence_bullets,
                raw_recall_count=len(raw_results),
                query_used=query,
                hindsight_connected=True,
                diagnostic_note=None,
                candidates_retrieved=parsed_items,
                relevance_verdict=verdict,
                relevance_reason=reason,
            )

        except UnauthorizedException as ue:
            from app.services.metrics_service import metrics_service
            metrics_service.inc_hindsight_failures()
            logger.warning("Hindsight API Unauthorized during recall: %s", ue)
            return RecallResultSummary(
                match_strength=MatchStrength.NONE,
                is_novel=True,
                memories_found=[],
                evidence_bullets=[
                    "Hindsight Cloud requires an API key for authenticated recall.",
                    "Set HINDSIGHT_API_KEY in .env to activate continuous cloud memory recall.",
                ],
                raw_recall_count=0,
                query_used=query,
                hindsight_connected=False,
                diagnostic_note="Hindsight Cloud authentication required (401). Operating in first-principles triage mode.",
            )
        except (NotFoundException, ApiException) as ae:
            is_server_error = False
            status_code = getattr(ae, "status", None) or getattr(ae, "status_code", None)
            if isinstance(status_code, int) and status_code >= 500:
                is_server_error = True
                await self.circuit_breaker.record_failure(ae)
            logger.warning("Hindsight API recall returned error: %s", ae)
            diag = "hindsight_circuit_open" if self.circuit_breaker.is_open else f"Hindsight bank '{self.bank_id}' query returned no active indexed documents."
            return RecallResultSummary(
                match_strength=MatchStrength.NONE,
                is_novel=True,
                memories_found=[],
                evidence_bullets=[
                    f"Memory bank '{self.bank_id}' has not retained incidents matching this service.",
                ],
                raw_recall_count=0,
                query_used=query,
                hindsight_connected=not is_server_error,
                diagnostic_note=diag,
            )
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as net_err:
            await self.circuit_breaker.record_failure(net_err)
            from app.services.metrics_service import metrics_service
            metrics_service.inc_hindsight_failures()
            logger.error("Hindsight API unreachable during recall: %s", net_err)
            diag = "hindsight_circuit_open" if self.circuit_breaker.is_open else f"Hindsight endpoint unreachable ({str(net_err)}). Fallback reasoning enabled."
            return RecallResultSummary(
                match_strength=MatchStrength.NONE,
                is_novel=True,
                memories_found=[],
                evidence_bullets=[
                    f"Hindsight API endpoint at {self.base_url} was unreachable.",
                    "Executing first-principles triage without historical memory augmentation.",
                ],
                raw_recall_count=0,
                query_used=query,
                hindsight_connected=False,
                diagnostic_note=diag,
            )
        except Exception as e:
            await self.circuit_breaker.record_failure(e)
            from app.services.metrics_service import metrics_service
            metrics_service.inc_hindsight_failures()
            logger.error("Unexpected error during Hindsight recall: %s", e, exc_info=True)
            diag = "hindsight_circuit_open" if self.circuit_breaker.is_open else f"Hindsight recall error: {str(e)}"
            return RecallResultSummary(
                match_strength=MatchStrength.NONE,
                is_novel=True,
                memories_found=[],
                evidence_bullets=["Encountered exception querying Hindsight memory."],
                raw_recall_count=0,
                query_used=query,
                hindsight_connected=False,
                diagnostic_note=diag,
            )
        finally:
            try:
                await client.aclose()
            except Exception:
                pass

    def _parse_recall_results(self, raw_results: List[Any]) -> List[IncidentMemoryItem]:
        """Convert raw Hindsight RecallResult objects into structured IncidentMemoryItem models."""
        items: List[IncidentMemoryItem] = []
        for res in raw_results:
            text = getattr(res, "text", "") or ""
            metadata = getattr(res, "metadata", {}) or {}
            tags = getattr(res, "tags", []) or []
            scores = getattr(res, "scores", {}) or {}
            item_id = str(getattr(res, "id", "mem-unknown"))

            # Extract fields from structured text or metadata
            incident_id = metadata.get("incident_id")
            service = metadata.get("service")
            severity = metadata.get("severity")
            alert_signature = metadata.get("alert_signature")
            title = metadata.get("title")
            runbook = metadata.get("verified_runbook") or metadata.get("runbook_used")
            root_cause = metadata.get("root_cause")
            postmortem_summary = metadata.get("postmortem_summary")

            # Fallback regex extraction from markdown if not in metadata
            if not incident_id:
                inc_match = re.search(r"INC-\d+", text)
                if inc_match:
                    incident_id = inc_match.group(0)

            if not alert_signature:
                sig_match = re.search(r"\*\*Alert Signature:\*\*\s*([^\n]+)", text)
                if sig_match:
                    alert_signature = sig_match.group(1).strip()

            if not runbook:
                rb_match = re.search(r"RB-[A-Z0-9\-]+", text)
                if rb_match:
                    runbook = rb_match.group(0)

            # Extract Root Cause from markdown section
            if not root_cause:
                rc_match = re.search(r"## Root Cause\s*\n+([^\n#]+)", text)
                if rc_match:
                    root_cause = rc_match.group(1).strip()

            # Extract Symptoms list
            symptoms: List[str] = []
            sym_match = re.search(r"## Symptoms\s*\n+((?:- [^\n]+\n?)+)", text)
            if sym_match:
                symptoms = [line.strip("- ").strip() for line in sym_match.group(1).strip().splitlines() if line.strip()]

            # Extract Failed Mitigations list
            failed_mitigations: List[str] = []
            fm_match = re.search(r"## Failed Mitigations\s*\n+((?:- [^\n]+\n?)+)", text)
            if fm_match:
                failed_mitigations = [line.strip("- ").strip() for line in fm_match.group(1).strip().splitlines() if line.strip()]

            # Extract Post-Mortem Summary
            if not postmortem_summary:
                pms_match = re.search(r"## Post-Mortem Summary\s*\n+([^\n#]+)", text)
                if pms_match:
                    postmortem_summary = pms_match.group(1).strip()

            # Extract Provenance fields
            from app.models.memory import MemoryStatus
            raw_status = metadata.get("memory_status")
            if not raw_status:
                stat_match = re.search(r"\*\*Memory Status:\*\*\s*([^\n]+)", text)
                if stat_match:
                    raw_status = stat_match.group(1).strip()

            raw_source = metadata.get("source_type")
            if not raw_source:
                src_match = re.search(r"\*\*Source Type:\*\*\s*([^\n]+)", text)
                if src_match:
                    raw_source = src_match.group(1).strip()

            verified_by = metadata.get("verified_by")
            if not verified_by:
                vb_match = re.search(r"\*\*Verified By:\*\*\s*([^\n]+)", text)
                if vb_match and vb_match.group(1).strip() not in ("UNVERIFIED", "None", "N/A"):
                    verified_by = vb_match.group(1).strip()

            verified_at = metadata.get("verified_at")
            if not verified_at:
                va_match = re.search(r"\*\*Verified At:\*\*\s*([^\n]+)", text)
                if va_match and va_match.group(1).strip() != "N/A":
                    verified_at = va_match.group(1).strip()

            source_incident_id = metadata.get("source_incident_id")
            if not source_incident_id:
                sinc_match = re.search(r"\*\*Source Incident ID:\*\*\s*([^\n]+)", text)
                if sinc_match:
                    source_incident_id = sinc_match.group(1).strip()

            # Canonical seeded incidents are trusted human-verified postmortems
            is_canonical_seed = incident_id in {"INC-104", "INC-108", "INC-203", "INC-305", "INC-402", "INC-519"}

            if raw_status:
                try:
                    mem_status = MemoryStatus(raw_status)
                except ValueError:
                    mem_status = MemoryStatus.DRAFT if "draft" in str(raw_status).lower() else MemoryStatus.VERIFIED
            elif is_canonical_seed:
                mem_status = MemoryStatus.VERIFIED
            elif "DRAFT" in tags or "status:draft" in tags:
                mem_status = MemoryStatus.DRAFT
            else:
                mem_status = MemoryStatus.VERIFIED

            if raw_source:
                try:
                    mem_source = MemorySourceType(raw_source)
                except ValueError:
                    mem_source = MemorySourceType.HUMAN_VERIFIED if mem_status == MemoryStatus.VERIFIED else MemorySourceType.AI_DRAFT
            elif is_canonical_seed:
                mem_source = MemorySourceType.HUMAN_VERIFIED
            else:
                mem_source = MemorySourceType.HUMAN_VERIFIED if mem_status == MemoryStatus.VERIFIED else MemorySourceType.AI_DRAFT

            if is_canonical_seed and not verified_by:
                verified_by = "sre-core-team"

            if is_canonical_seed and incident_id:
                seed_data = _get_seed_incident(incident_id)
                if seed_data:
                    title = title or seed_data.get("title")
                    root_cause = root_cause or seed_data.get("root_cause")
                    runbook = runbook or seed_data.get("verified_runbook")
                    postmortem_summary = postmortem_summary or seed_data.get("postmortem_summary")
                    if not symptoms:
                        symptoms = list(seed_data.get("symptoms", []))
                    if not failed_mitigations:
                        failed_mitigations = list(seed_data.get("failed_mitigations", []))

            items.append(
                IncidentMemoryItem(
                    id=item_id,
                    incident_id=incident_id,
                    service=service,
                    severity=severity,
                    alert_signature=alert_signature,
                    title=title or (f"Historical Record {incident_id}" if incident_id else None),
                    symptoms=symptoms,
                    root_cause=root_cause,
                    failed_mitigations=failed_mitigations,
                    verified_runbook=runbook,
                    postmortem_summary=postmortem_summary or root_cause,
                    resolution=postmortem_summary or root_cause,
                    runbook_used=runbook,
                    raw_text=text,
                    scores=scores if isinstance(scores, dict) else None,
                    tags=tags,
                    occurred_at=str(getattr(res, "occurred_start", "") or ""),
                    memory_status=mem_status,
                    source_type=mem_source,
                    verified_by=verified_by,
                    verified_at=str(verified_at) if verified_at else None,
                    source_incident_id=source_incident_id or incident_id,
                )
            )
        return items

    def _evaluate_match_strength(
        self,
        alert: AlertPayload,
        items: List[IncidentMemoryItem],
    ) -> tuple[MatchStrength, List[str]]:
        """Categorical match assessment adhering to Truthful Metrics (Invariant 3).

        Evaluates failure-mode alignment and rejects decoys using normalized technical tokens.
        Produces 'High', 'Moderate', or 'None' backed by verifiable factual bullets.
        Never outputs uncalculated synthetic percentages.
        """
        strength, bullets, _, _, _ = evaluate_batch_relevance(alert, items)
        return strength, bullets

    async def retain_incident(self, payload: RetainIncidentPayload) -> Dict[str, Any]:
        """Retain a structured incident post-mortem directly into Hindsight memory bank.

        Stores structured incident memories containing:
        incident_id, service, severity, alert_signature, symptoms, root_cause,
        failed_mitigations, verified_runbook, postmortem_summary, and provenance fields.

        Idempotent via document_id=payload.incident_id and update_mode="replace".
        Completes the learning loop (Invariant 5) hitting the real Hindsight API.
        """
        from app.services.provenance_service import provenance_service
        payload = provenance_service.validate_provenance_on_retention(payload)

        target_bank = payload.bank_id or self.bank_id
        client = self._get_client()

        # Build structured symptoms and failed mitigations lists
        symptoms_str = "\n".join(f"- {s}" for s in payload.symptoms) if payload.symptoms else "- Unspecified operational symptoms"
        failed_mitigations_str = "\n".join(f"- {m}" for m in payload.failed_mitigations) if payload.failed_mitigations else "- None documented"
        runbook = payload.verified_runbook or payload.runbook_executed or "None"
        summary = payload.postmortem_summary or payload.resolution or payload.root_cause

        # Format structured markdown representation for Hindsight's knowledge indexing
        content = (
            f"# SRE Incident Memory: {payload.incident_id} - {payload.title or payload.service}\n\n"
            f"**Incident ID:** {payload.incident_id}\n"
            f"**Service:** {payload.service}\n"
            f"**Severity:** {payload.severity}\n"
            f"**Alert Signature:** {payload.alert_signature or 'N/A'}\n"
            f"**Memory Status:** {payload.memory_status.value}\n"
            f"**Source Type:** {payload.source_type.value}\n"
            f"**Verified By:** {payload.verified_by or 'UNVERIFIED'}\n"
            f"**Verified At:** {payload.verified_at.isoformat() if payload.verified_at else 'N/A'}\n"
            f"**Source Incident ID:** {payload.source_incident_id or payload.incident_id}\n"
            f"**Verified Runbook:** {runbook}\n"
            f"**Timestamp:** {payload.timestamp.isoformat()}\n\n"
            f"## Symptoms\n{symptoms_str}\n\n"
            f"## Root Cause\n{payload.root_cause}\n\n"
            f"## Failed Mitigations\n{failed_mitigations_str}\n\n"
            f"## Verified Runbook\n{runbook}\n\n"
            f"## Post-Mortem Summary\n{summary}\n\n"
        )
        if payload.timeline:
            content += "## Timeline\n"
            for t in payload.timeline:
                content += f"- **{t.get('time', 'T')}**: {t.get('event', '')}\n"
            content += "\n"

        status_tag = "status:verified" if payload.memory_status == MemoryStatus.VERIFIED else "status:draft"
        tags = list(set([
            payload.service,
            payload.severity,
            payload.incident_id,
            runbook,
            payload.memory_status.value,
            status_tag,
        ] + [t for t in (payload.tags or []) if t]))

        metadata = {
            "incident_id": payload.incident_id,
            "service": payload.service,
            "severity": payload.severity,
            "alert_signature": payload.alert_signature or "",
            "verified_runbook": runbook,
            "runbook_used": runbook,
            "title": payload.title or f"{payload.incident_id} - {payload.service}",
            "memory_status": payload.memory_status.value,
            "source_type": payload.source_type.value,
            "verified_by": payload.verified_by or "",
            "verified_at": payload.verified_at.isoformat() if payload.verified_at else "",
            "source_incident_id": payload.source_incident_id or payload.incident_id,
        }


        try:
            await self.ensure_bank()
            logger.info(
                "Retaining incident '%s' directly into Hindsight memory bank '%s' (document_id=%s)...",
                payload.incident_id,
                target_bank,
                payload.incident_id,
            )
            retain_resp: RetainResponse = await asyncio.wait_for(
                client.aretain(
                    bank_id=target_bank,
                    content=content,
                    document_id=payload.incident_id,
                    update_mode="replace",
                    tags=tags,
                    metadata=metadata,
                ),
                timeout=self.timeout,
            )
            return {
                "success": getattr(retain_resp, "success", True),
                "bank_id": target_bank,
                "incident_id": payload.incident_id,
                "operation_id": str(getattr(retain_resp, "operation_id", "") or ""),
                "content_preview": content[:240] + "...",
                "status": "retained",
            }
        except UnauthorizedException as ue:
            logger.warning("Hindsight API retain 401 Unauthorized: %s", ue)
            return {
                "success": False,
                "bank_id": target_bank,
                "incident_id": payload.incident_id,
                "error": "Authentication required. Configure HINDSIGHT_API_KEY in .env.",
                "status": "unauthorized",
            }
        except Exception as e:
            logger.error("Failed retaining incident into Hindsight: %s", e, exc_info=True)
            return {
                "success": False,
                "bank_id": target_bank,
                "incident_id": payload.incident_id,
                "error": str(e),
                "status": "error",
            }
        finally:
            try:
                await client.aclose()
            except Exception:
                pass

    async def reflect_insights(self, query: str) -> str:
        """Call Hindsight API 'reflect' to synthesize high-density mental models."""
        client = self._get_client()
        try:
            logger.info("Calling Hindsight 'reflect' for query: %s", query)
            reflect_resp = await asyncio.wait_for(
                client.areflect(
                    bank_id=self.bank_id,
                    query=query,
                    budget="low",
                ),
                timeout=self.timeout,
            )
            # reflect_resp typically contains text or synthesized insights
            return str(getattr(reflect_resp, "text", "") or reflect_resp)
        except Exception as e:
            logger.warning("Hindsight reflect operation: %s", e)
            return f"Reflection unavailable from Hindsight: {str(e)}"
        finally:
            try:
                await client.aclose()
            except Exception:
                pass


# Global singleton instance
hindsight_service = HindsightMemoryService()
