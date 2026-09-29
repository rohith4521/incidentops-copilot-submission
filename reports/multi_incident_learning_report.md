# IncidentOps Copilot — Multi-Incident Continuous Learning Evaluation Report

## Executive Summary
This evaluation measures the **operational knowledge accumulation** and **provenance safety lifecycle** of IncidentOps Copilot across sequential incidents.

It demonstrates how the system evolves over time:
1. Ingesting diverse incident failure modes across multiple microservices.
2. Enforcing the strict **DRAFT → HUMAN VERIFIED → VERIFIED MEMORY** lifecycle.
3. Building an authoritative memory bank of proven runbooks and known anti-patterns (failed mitigations).
4. Accurately recalling relevant precedents for paraphrased alerts.
5. Reliably rejecting lookalikes, decoys with misleading generic vocabulary, and unrelated failure modes on the same service.
6. Strictly isolating unverified AI drafts from influencing trusted historical precedent.

**Execution Mode**: Deterministic Offline Memory Boundary  
**Evaluation Status**: ✅ ALL TESTS PASSED

---

## 1. Key Evaluation Metrics

| Metric | Target | Result | Ground Truth Sample | Evaluation Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **Verified Memories Accumulated** | ≥ 5 | **5** | 5 operational incidents | Verified by SRE with immutable provenance audit |
| **Unverified Drafts Isolated** | ≥ 1 | **1** | 1 unverified draft | Preserved for audit; rejected from trusted precedent |
| **Relevant Precedent Retrieval** | 100.0% | **100.0%** | 2/2 | Paraphrased alerts recall expected historical incidents |
| **Irrelevant Precedent Rejection** | 100.0% | **100.0%** | 3/3 | Lookalikes, decoys, and same-service different domains rejected |
| **Novel Incident Detection** | 100.0% | **100.0%** | 1/1 | Unseen failure modes detected with 0 historical matches |
| **Draft Postmortem Isolation** | 100.0% | **100.0%** | 1/1 | Unverified AI draft rejected by provenance gate |
| **Runbook Grounding Rate** | 100.0% | **100.0%** | Recalled cases | Recommended runbook precisely matches verified precedent |
| **Failed Mitigations Grounding** | 100.0% | **100.0%** | Recalled cases | Documented failed mitigations warned to SRE |
| **Provenance Integrity** | 100.0% | **100.0%** | All training cases | Zero unearned trust escalation |

---

## 2. Training Phase: Knowledge Accumulation & Provenance Audit

Each incident was processed through the continuous learning pipeline:
1. Alert ingestion triggered triage (verifying `novelty=True` on initial occurrence).
2. AI draft postmortem generated with status `DRAFT` and `source_type=AI_DRAFT`.
3. Human SRE (`oncall-sre`) reviewed and verified operational resolution.
4. Retention into persistent memory with `status=VERIFIED`.

| Incident ID | Service | Final Status | Verified By | Verified Runbook | Anti-Patterns |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `INC-SEQ-001` | `billing-service` | **VERIFIED** | `oncall-sre` | `RB-BILLING-SERIALIZE-TX` | 2 |
| `INC-SEQ-002` | `billing-service` | **VERIFIED** | `oncall-sre` | `RB-GATEWAY-CIRCUIT-TRIP` | 2 |
| `INC-SEQ-003` | `auth-service` | **VERIFIED** | `oncall-sre` | `RB-AUTH-WARM-KEYSET` | 2 |
| `INC-SEQ-004` | `catalog-service` | **VERIFIED** | `oncall-sre` | `RB-CATALOG-STAGGER-TTL` | 2 |
| `INC-SEQ-005` | `event-streaming-hub` | **VERIFIED** | `oncall-sre` | `RB-KAFKA-EXTEND-MAX-POLL` | 2 |
| `INC-SEQ-006` | `search-service` | **DRAFT** | *None (Draft)* | `RB-UNVERIFIED-SEARCH-DRAFT` | 1 |

---

## 3. Evaluation Phase: Accumulated Memory Recall & Precision

Follow-up alerts were evaluated against the accumulated memory bank:

| Alert ID | Service | Query Category | Result | Recalled Precedent | Match Strength | Grounded Runbook | Anti-Patterns | Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `EVAL-ALERT-1` | `billing-service` | paraphrased_repeat | ✅ Pass | `INC-SEQ-001` | [High] | `RB-BILLING-SERIALIZE-TX` | 2 | 0.92ms |
| `EVAL-ALERT-2` | `auth-service` | misleading_generic_decoy | ✅ Pass | *None* | [None] | `RB-AUTH-SERVICE-DIAGNOSTIC-ISOLATE` | 3 | 0.77ms |
| `EVAL-ALERT-3` | `billing-service` | same_service_different_domain | ✅ Pass | *None* | [None] | `RB-BILLING-SERVICE-DIAGNOSTIC-ISOLATE` | 3 | 0.96ms |
| `EVAL-ALERT-4` | `catalog-service` | paraphrased_repeat | ✅ Pass | `INC-SEQ-004` | [High] | `RB-CATALOG-STAGGER-TTL` | 2 | 0.68ms |
| `EVAL-ALERT-5` | `ml-inference-gateway` | genuinely_novel | ✅ Pass | *None* | [None] | `RB-ML-INFERENCE-GATEWAY-DIAGNOSTIC-ISOLATE` | 3 | 0.31ms |
| `EVAL-ALERT-6` | `search-service` | draft_isolation_test | ✅ Pass | *None* | [None] | `RB-SEARCH-SERVICE-DIAGNOSTIC-ISOLATE` | 3 | 0.47ms |
| `EVAL-ALERT-7` | `billing-service` | stateless_mode | ✅ Pass | *None* | [None] | `RB-BILLING-SERVICE-STATELESS-TRIAGE` | 2 | 0.57ms |

---

## 4. Architectural Findings & Invariant Verification

1. **Same-Service Failure Mode Disambiguation**:
   - `billing-service` accumulated two distinct verified memories: `INC-SEQ-001` (Postgres row deadlock) and `INC-SEQ-002` (Stripe gateway timeout).
   - When a Postgres deadlock alert occurred, the system recalled and accepted `INC-SEQ-001` while correctly rejecting `INC-SEQ-002`.
   - When a container OOM alert occurred on `billing-service`, the system rejected **both** incidents because the failure domain differed.

2. **Resistance to Misleading Generic Vocabulary**:
   - `EVAL-ALERT-2` on `auth-service` contained standard SRE buzzwords (*"high latency"*, *"p99 spike"*, *"downstream timeout"*).
   - Because the underlying failure was an expired LDAP certificate rather than the token signing stampede in `INC-SEQ-003`, the relevance gate rejected the candidate (`REJECTED_LOW_RELEVANCE`).

3. **Strict Draft Postmortem Isolation**:
   - `INC-SEQ-006` was retained as an unverified `DRAFT`.
   - `EVAL-ALERT-6` retrieved `INC-SEQ-006` during candidate search, but the provenance gate immediately rejected it (`REJECTED_UNVERIFIED_DRAFT_MEMORY`).
   - The incident was treated as novel, preventing unverified AI assertions from acting as trusted precedent.

4. **Runbook and Anti-Pattern Grounding**:
   - For every accepted match, the verified remediation runbook was promoted.
   - Dangerous trial-and-error actions (e.g. *"increasing worker concurrency worsened lock contention"*) were extracted from memory and flagged as failed mitigations to avoid.
