# IncidentOps Copilot — Held-Out Memory Evaluation Report (Phase 6.6A)

> [!IMPORTANT]
> **Scope Notice**: Results in this evaluation report apply **strictly to this held-out synthetic dataset** and reflect deterministic offline benchmarks without modifying production relevance logic.

## 1. Executive Summary & Dataset Composition

- **Dataset Size**: 16 operational incident alerts
- **Scenario Categories**:
  - `paraphrased_variant`: 5 alerts (paraphrases of verified incident families)
  - `decoy`: 5 alerts (same service, but conflicting failure domains)
  - `novel`: 4 alerts (genuinely unseen microservices/failure modes)
  - `unverified_memory`: 2 alerts (matching unverified AI drafts in memory)

---

## 2. Core Evaluation Metrics

| Metric | Ground Truth Requirement | Result Rate | Raw Count | Evaluation Status |
| :--- | :--- | :--- | :--- | :--- |
| **Relevant Precedent Retrieval** | Recalls verified incident for paraphrased alerts | **100.0%** | 5/5 | Passed |
| **Decoy False-Match Rate (FPR)** | Rejects lookalike alerts with domain conflict | **0.0%** | 0/5 | Passed |
| **Decoy Specificity / Correct Rejection** | Correctly rejects unrelated failure modes | **100.0%** | 5/5 | Passed |
| **Novel False-Match Rate** | Does not fabricate precedent for unseen services | **0.0%** | 0/4 | Passed |
| **Unverified-Memory Rejection** | Rejects unverified AI draft postmortems | **100.0%** | 2/2 | Passed |
| **Runbook Grounding** | Grounds proven runbook upon verified match | **100.0%** | 5/5 | Passed |

---

## 3. Memory ON vs Memory OFF Comparison

| Evaluation Dimension | Memory ON (Hindsight Recall) | Memory OFF (Stateless Mode) | Delta / Operational Value |
| :--- | :--- | :--- | :--- |
| **Precedent Recall Rate** | **100.0%** (5/5) | **0.0%** (0/5) | +100.0% historical guidance |
| **Proven Runbook Grounding** | **100.0%** (5/5) | **0.0%** (0/5) | +100.0% grounded runbooks |
| **Anti-Patterns Grounded** | **2.0 / case** | **0.0 / case** | Early prevention of dead-end actions |
| **Average Recall Latency** | **1.166 ms** | **0.002 ms** | Deterministic in-memory execution |

---

## 4. Replay-Curve Evaluation (Continuous Knowledge Accumulation)

The replay curve begins with zero relevant operational memories and incrementally ingests and verifies incidents one by one. At each stage, the complete suite of follow-up alerts is evaluated.

| Stage | Verified Incident Ingested | Bank Size | Follow-up Recalled | Recall Rate | First Recalled Alert |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Step 0 | `None (Base)` | 0 | 0/5 | **0.0%** | None |
| Step 1 | `INC-104` | 1 | 1/5 | **20.0%** | `HELD-OUT-PARA-001` |
| Step 2 | `INC-108` | 2 | 2/5 | **40.0%** | `HELD-OUT-PARA-002` |
| Step 3 | `INC-203` | 3 | 3/5 | **60.0%** | `HELD-OUT-PARA-003` |
| Step 4 | `INC-305` | 4 | 4/5 | **80.0%** | `HELD-OUT-PARA-004` |
| Step 5 | `INC-402` | 5 | 5/5 | **100.0%** | `HELD-OUT-PARA-005` |

**Curve Characteristic**: Strictly monotonic non-decreasing (0.0% -> 100.0%). Retrieval capability scales directly with verified incident retention.

---

## 5. Itemized Test Results (Memory ON)

| Case ID | Category | Target Service | Matched | Recalled Incident | Strength | Grounded Runbook | Failed Mitigations | Correct |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `HELD-OUT-PARA-001` | paraphrased_variant | `payment-api` | Yes | `INC-104` | High | `RB-PAYMENT-CIRCUIT-SHED` | 2 | Yes |
| `HELD-OUT-PARA-002` | paraphrased_variant | `order-db-primary` | Yes | `INC-108` | High | `RB-PG-KILL-LOCKS-ORDER-SORT` | 2 | Yes |
| `HELD-OUT-PARA-003` | paraphrased_variant | `auth-cache-service` | Yes | `INC-203` | High | `RB-REDIS-EVICTION-TUNE-SCALE` | 2 | Yes |
| `HELD-OUT-PARA-004` | paraphrased_variant | `event-queue-worker` | Yes | `INC-305` | High | `RB-KAFKA-SKIP-OFFSET-TO-DLQ` | 2 | Yes |
| `HELD-OUT-PARA-005` | paraphrased_variant | `checkout-service` | Yes | `INC-402` | High | `RB-REDIS-FAILOVER` | 2 | Yes |
| `HELD-OUT-DECOY-001` | decoy | `payment-api` | No | `None` | None | `None` | 0 | Yes |
| `HELD-OUT-DECOY-002` | decoy | `order-db-primary` | No | `None` | None | `None` | 0 | Yes |
| `HELD-OUT-DECOY-003` | decoy | `auth-cache-service` | No | `None` | None | `None` | 0 | Yes |
| `HELD-OUT-DECOY-004` | decoy | `event-queue-worker` | No | `None` | None | `None` | 0 | Yes |
| `HELD-OUT-DECOY-005` | decoy | `checkout-service` | No | `None` | None | `None` | 0 | Yes |
| `HELD-OUT-NOVEL-001` | novel | `inventory-sync-service` | No | `None` | None | `None` | 0 | Yes |
| `HELD-OUT-NOVEL-002` | novel | `notification-dispatcher` | No | `None` | None | `None` | 0 | Yes |
| `HELD-OUT-NOVEL-003` | novel | `shipping-rate-calculator` | No | `None` | None | `None` | 0 | Yes |
| `HELD-OUT-NOVEL-004` | novel | `search-indexer-daemon` | No | `None` | None | `None` | 0 | Yes |
| `HELD-OUT-UNVERIFIED-001` | unverified_memory | `billing-worker` | No | `None` | None | `None` | 0 | Yes |
| `HELD-OUT-UNVERIFIED-002` | unverified_memory | `analytics-pipeline` | No | `None` | None | `None` | 0 | Yes |
