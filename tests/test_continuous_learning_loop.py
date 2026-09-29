"""Phase 4: Continuous Learning Loop Integration Tests.

Validates the full operational lifecycle:
1. Novel Alert Ingestion
   -> Triage determines novelty=True + historical_matches=[]
2. Draft & Retain Post-Mortem into Hindsight memory bank
   -> Commits verified runbook, root cause, symptoms, and failed mitigations
3. Repeat Same / Similar Alert Ingestion
   -> Triage determines novelty=False
   -> Historical match recalled (citing newly retained incident)
   -> Proven verified runbook recalled
   -> Failed mitigations to avoid recalled
4. Memory Toggle Invariant Check
   -> Stateless mode (enable_memory=False) ignores newly retained memory.
"""

from typing import List
from unittest.mock import AsyncMock, patch
import pytest

from app.models.alert import AlertPayload, AlertSeverity
from app.models.memory import (
    IncidentMemoryItem,
    MatchStrength,
    RecallResultSummary,
    RetainIncidentPayload,
)
from app.services.hindsight_service import hindsight_service


@pytest.fixture
def mock_continuous_hindsight():
    """Simulates the Hindsight API storage boundary for the continuous learning lifecycle.

    Reuses the REAL hindsight_service._evaluate_match_strength matching algorithm.
    Does not create any mock memory layer in production code.
    """
    memory_bank: List[IncidentMemoryItem] = []

    async def mock_retain(payload: RetainIncidentPayload):
        item = IncidentMemoryItem(
            id=f"mem-{payload.incident_id.lower()}",
            incident_id=payload.incident_id,
            service=payload.service,
            severity=payload.severity,
            alert_signature=payload.alert_signature,
            title=payload.title or f"{payload.incident_id} - {payload.service}",
            symptoms=payload.symptoms,
            root_cause=payload.root_cause,
            failed_mitigations=payload.failed_mitigations,
            verified_runbook=payload.verified_runbook,
            runbook_used=payload.verified_runbook,
            postmortem_summary=payload.postmortem_summary,
            resolution=payload.resolution or payload.postmortem_summary,
            tags=payload.tags,
            raw_text=(
                f"{payload.service} {payload.root_cause} {payload.verified_runbook} "
                f"{' '.join(payload.symptoms)} {' '.join(payload.failed_mitigations)}"
            ),
        )
        # Update or append (idempotent replacement)
        existing_idx = next(
            (i for i, m in enumerate(memory_bank) if m.incident_id == payload.incident_id),
            None,
        )
        if existing_idx is not None:
            memory_bank[existing_idx] = item
        else:
            memory_bank.append(item)

        return {
            "success": True,
            "bank_id": payload.bank_id or "sre-incidentops-production",
            "incident_id": payload.incident_id,
            "operation_id": f"op-retain-{payload.incident_id}",
            "content_preview": f"Retained {payload.incident_id} ({payload.service})",
            "status": "retained",
        }

    async def mock_recall(alert: AlertPayload) -> RecallResultSummary:
        if not memory_bank:
            return RecallResultSummary(
                match_strength=MatchStrength.NONE,
                is_novel=True,
                memories_found=[],
                evidence_bullets=[
                    f"No historical incidents found in Hindsight memory for service '{alert.service}'."
                ],
                raw_recall_count=0,
                query_used=alert.title,
                hindsight_connected=True,
            )

        # Execute the REAL hindsight_service matching evaluation logic
        strength, bullets = hindsight_service._evaluate_match_strength(alert, memory_bank)
        is_novel = strength == MatchStrength.NONE

        matched_items = (
            [
                m for m in memory_bank
                if (m.service and m.service.lower() == alert.service.lower())
                or any(s.lower() in m.raw_text.lower() for s in alert.symptoms)
            ]
            if not is_novel
            else []
        )

        return RecallResultSummary(
            match_strength=strength,
            is_novel=is_novel,
            memories_found=matched_items,
            evidence_bullets=bullets,
            raw_recall_count=len(matched_items),
            query_used=alert.title,
            hindsight_connected=True,
        )

    with patch.object(
        hindsight_service, "retain_incident", new_callable=AsyncMock, side_effect=mock_retain
    ), patch.object(
        hindsight_service, "recall_incident_memory", new_callable=AsyncMock, side_effect=mock_recall
    ):
        yield memory_bank


def test_continuous_learning_full_lifecycle(client, mock_continuous_hindsight):
    """End-to-end continuous learning loop:

    Phase 4: NEW INCIDENT -> TRIAGE -> POSTMORTEM -> HINDSIGHT RETAIN -> REPEAT ALERT -> HINDSIGHT RECALL
    """
    novel_incident_id = "INC-701"
    target_service = "vector-search-indexer"
    alert_title = "RocksDBWriteStallAndSegmentCorruption"
    symptoms = [
        "RocksDB write stall duration exceeded 15000ms",
        "Merge thread pool starvation on SST index partitions",
        "Cascading unhandled I/O read panic on shard 4",
    ]

    # =========================================================================
    # STEP 1: Ingest NOVEL Incident Alert
    # =========================================================================
    novel_alert_payload = {
        "service": target_service,
        "alert": alert_title,
        "symptoms": symptoms,
        "severity": "CRITICAL",
        "context": {"cluster": "k8s-prod-us-central-1", "shard": "shard-4"},
        "enable_memory": True,
    }

    triage_1_resp = client.post("/api/triage", json=novel_alert_payload)
    assert triage_1_resp.status_code == 200
    triage_1 = triage_1_resp.json()

    # Step 1 Invariant Assertions: Novelty Flag MUST be True, NO historical matches
    assert triage_1["memory_used"] is True
    assert triage_1["novelty"] is True, "First occurrence of novel alert must have novelty=True"
    assert triage_1["historical_matches"] == [], "Novel incident must not fabricate historical matches"
    assert "No sufficiently relevant historical incident found" in triage_1["incident_summary"]
    assert triage_1["requires_human_approval"] is True
    assert triage_1["recommended_runbook"] is not None
    assert triage_1["recommended_runbook"]["status"] == "PENDING_APPROVAL"

    # =========================================================================
    # STEP 2: SRE Drafts Post-Mortem from Triage Result
    # =========================================================================
    draft_req = {
        "triage_result": {
            "incident_id": novel_incident_id,
            "alert_id": "ALT-VEC-001",
            "match_strength": "None",
            "novelty_detected": True,
            "triage_summary": triage_1["incident_summary"],
            "root_cause_analysis": {
                "hypothesis": "Corrupt RocksDB SST segment caused unhandled I/O panic and merge thread starvation.",
                "blast_radius": f"{target_service} shard-4",
                "contributing_factors": symptoms,
                "affected_components": [target_service],
            },
            "immediate_mitigation": "Isolate corrupted SST index and rebuild shard from clean WAL checkpoint.",
            "recommended_runbook": triage_1["recommended_runbook"],
            "requires_human_intervention": True,
        },
        "incident_title": "RocksDB SST Partition Checksum Corruption & Thread Starvation",
        "confirmed_resolution": "Applied RB-ROCKSDB-DYNAMIC-THROTTLE to isolate corrupt SST segment and rebuild shard from WAL.",
        "runbook_executed": "RB-ROCKSDB-DYNAMIC-THROTTLE",
    }

    draft_resp = client.post("/api/postmortems/draft", json=draft_req)
    assert draft_resp.status_code == 200
    draft_data = draft_resp.json()
    assert draft_data["service"] == target_service
    assert draft_data["runbook_executed"] == "RB-ROCKSDB-DYNAMIC-THROTTLE"
    assert len(draft_data["timeline"]) > 0

    # =========================================================================
    # STEP 3: Retain Post-Mortem into Hindsight Persistent Memory
    # =========================================================================
    retain_payload = {
        "bank_id": "sre-incidentops-production",
        "incident_id": novel_incident_id,
        "service": target_service,
        "severity": "CRITICAL",
        "alert_signature": alert_title,
        "title": "RocksDB SST Partition Checksum Corruption & Thread Starvation",
        "symptoms": symptoms,
        "root_cause": "Corrupt RocksDB SST segment caused unhandled I/O panic and merge thread starvation under high ingest.",
        "failed_mitigations": [
            "Restarting vector-search-indexer pods alone caused immediate crashloop retry storm on corrupt SST files.",
            "Increasing merge thread pool count worsened disk I/O saturation and write stall.",
        ],
        "verified_runbook": "RB-ROCKSDB-DYNAMIC-THROTTLE",
        "postmortem_summary": "Resolved by isolating corrupted SST segment and rebuilding shard from clean WAL via RB-ROCKSDB-DYNAMIC-THROTTLE.",
        "resolution": "Applied RB-ROCKSDB-DYNAMIC-THROTTLE: throttled background compaction, purged corrupt SST segment, and replayed WAL.",
        "tags": [target_service, "rocksdb", "sst-corruption", "RB-ROCKSDB-DYNAMIC-THROTTLE", novel_incident_id],
    }

    retain_resp = client.post(
        "/api/postmortem/retain",
        json=retain_payload,
        headers={"X-API-Key": "sre-key-oncall"},
    )
    assert retain_resp.status_code == 200
    retain_data = retain_resp.json()
    assert retain_data["success"] is True
    assert retain_data["incident_id"] == novel_incident_id
    assert retain_data["bank_id"] == "sre-incidentops-production"

    # Confirm memory item is stored in the boundary
    assert len(mock_continuous_hindsight) == 1
    assert mock_continuous_hindsight[0].incident_id == novel_incident_id

    # =========================================================================
    # STEP 4: Ingest REPEAT Alert for the Same Service & Failure Signature
    # =========================================================================
    repeat_alert_payload = {
        "service": target_service,
        "alert": "RocksDBWriteStallAndSegmentCorruptionRecurring",
        "symptoms": [
            "RocksDB write stall duration exceeded 15000ms",
            "Merge thread pool starvation on SST index partitions",
            "Unhandled I/O read panic on shard 4",
        ],
        "severity": "CRITICAL",
        "context": {"cluster": "k8s-prod-us-central-1", "shard": "shard-4"},
        "enable_memory": True,
    }

    triage_2_resp = client.post("/api/triage", json=repeat_alert_payload)
    assert triage_2_resp.status_code == 200
    triage_2 = triage_2_resp.json()

    # =========================================================================
    # STEP 5: Continuous Learning Recall Verification
    # =========================================================================
    assert triage_2["memory_used"] is True

    # 1. Novelty MUST flip from True to False!
    assert triage_2["novelty"] is False, "Repeat alert MUST have novelty=False after Hindsight retention"

    # 2. Historical matches must now recall INC-701!
    matches = triage_2["historical_matches"]
    assert len(matches) > 0, "Hindsight memory recall must find the retained post-mortem"
    recalled_ids = [m["incident_id"] for m in matches]
    assert novel_incident_id in recalled_ids, f"Expected {novel_incident_id} in recalled matches {recalled_ids}"

    matched_item = next(m for m in matches if m["incident_id"] == novel_incident_id)
    assert matched_item["service"] == target_service
    assert matched_item["verified_runbook"] == "RB-ROCKSDB-DYNAMIC-THROTTLE"

    # 3. Verified runbook MUST be recommended!
    recommended_rb = triage_2["recommended_runbook"]
    assert recommended_rb is not None
    assert recommended_rb["runbook_id"] == "RB-ROCKSDB-DYNAMIC-THROTTLE"
    assert recommended_rb["status"] == "PENDING_APPROVAL"
    assert triage_2["requires_human_approval"] is True

    # 4. Retained failed mitigations to avoid MUST be recalled!
    failed_mitigations = triage_2["failed_mitigations_to_avoid"]
    assert len(failed_mitigations) > 0
    assert any("Restarting vector-search-indexer pods" in fm for fm in failed_mitigations), (
        f"Failed mitigations should recall the warned actions: {failed_mitigations}"
    )

    # =========================================================================
    # STEP 6: Memory Toggle Invariant Check (enable_memory=False)
    # =========================================================================
    stateless_repeat_payload = dict(repeat_alert_payload)
    stateless_repeat_payload["enable_memory"] = False

    triage_stateless_resp = client.post("/api/triage", json=stateless_repeat_payload)
    assert triage_stateless_resp.status_code == 200
    triage_stateless = triage_stateless_resp.json()

    assert triage_stateless["memory_used"] is False
    assert triage_stateless["novelty"] is True
    assert triage_stateless["historical_matches"] == []
    assert "Stateless" in triage_stateless["incident_summary"]
