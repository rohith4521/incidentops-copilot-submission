# SRE Diagnosis Quality Benchmark Report (Phase 7.5)
**Date:** 2026-09-29 13:24:14 UTC
**Dataset Size:** 16 total scenarios

## 1. Executive Summary & Aggregate Accuracy
| Metric | Memory OFF (Stateless) | Memory ON (Hindsight) | Absolute Difference | Relative Impact |
| :--- | :--- | :--- | :--- | :--- |
| **Root-Cause Accuracy** | 93.75% | 93.75% | +0.0% | Neutral |
| **Runbook Recommendation Accuracy** | 0.0% | 50.0% | +50.0% | Substantial Improvement |
| **False Historical Grounding Rate** | 0.0% | 0.0% | +0.0% | Low / Controlled |
| **Novel Incident False Grounding Rate** | 0.0% | 0.0% | +0.0% | Zero False Positives on Novel |
| **Retrieval Correctness Rate** | N/A (Memory OFF) | 100.0% | N/A | Evaluates Hindsight Precision/Recall |
| **Evidence Correctness Rate** | 100.0% (No Hallucination) | 100.0% | +0.0% | Verified Factual Evidence Grounding |

## 2. Category Breakdown (Known vs Novel)
| Category | Count | Diag Acc (OFF) | Diag Acc (ON) | Diag Delta | Runbook Acc (OFF) | Runbook Acc (ON) | Runbook Delta |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Known** | 4 | 100.0% | 100.0% | +0.0% | 0.0% | 100.0% | +100.0% |
| **Paraphrased** | 4 | 100.0% | 100.0% | +0.0% | 0.0% | 100.0% | +100.0% |
| **Decoy** | 4 | 75.0% | 75.0% | +0.0% | 0.0% | 0.0% | +0.0% |
| **Novel** | 4 | 100.0% | 100.0% | +0.0% | 0.0% | 0.0% | +0.0% |

## 3. Per-Scenario Evaluation Results
| ID | Category | Service | Has Precedent | OFF Diag | ON Diag | OFF Runbook | ON Runbook | ON Matches | False Grounding |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `BENCH-KNOWN-001` | known | `payment-api` | True | PASS | PASS | FAIL | PASS | `INC-104` | NO |
| `BENCH-KNOWN-002` | known | `order-db-primary` | True | PASS | PASS | FAIL | PASS | `INC-108` | NO |
| `BENCH-KNOWN-003` | known | `auth-cache-service` | True | PASS | PASS | FAIL | PASS | `INC-203` | NO |
| `BENCH-KNOWN-004` | known | `event-queue-worker` | True | PASS | PASS | FAIL | PASS | `INC-305` | NO |
| `BENCH-PARA-005` | paraphrased | `checkout-service` | True | PASS | PASS | FAIL | PASS | `INC-402` | NO |
| `BENCH-PARA-006` | paraphrased | `auth-api` | True | PASS | PASS | FAIL | PASS | `INC-519` | NO |
| `BENCH-PARA-007` | paraphrased | `payment-api` | True | PASS | PASS | FAIL | PASS | `INC-104` | NO |
| `BENCH-PARA-008` | paraphrased | `order-db-primary` | True | PASS | PASS | FAIL | PASS | `INC-108` | NO |
| `BENCH-DECOY-009` | decoy | `payment-api` | False | PASS | PASS | FAIL | FAIL | `None` | NO |
| `BENCH-DECOY-010` | decoy | `order-db-primary` | False | PASS | PASS | FAIL | FAIL | `None` | NO |
| `BENCH-DECOY-011` | decoy | `auth-cache-service` | False | PASS | PASS | FAIL | FAIL | `None` | NO |
| `BENCH-DECOY-012` | decoy | `event-queue-worker` | False | FAIL | FAIL | FAIL | FAIL | `None` | NO |
| `BENCH-NOVEL-013` | novel | `search-indexer` | False | PASS | PASS | FAIL | FAIL | `None` | NO |
| `BENCH-NOVEL-014` | novel | `notification-gateway` | False | PASS | PASS | FAIL | FAIL | `None` | NO |
| `BENCH-NOVEL-015` | novel | `billing-ledger` | False | PASS | PASS | FAIL | FAIL | `None` | NO |
| `BENCH-NOVEL-016` | novel | `graphql-gateway` | False | PASS | PASS | FAIL | FAIL | `None` | NO |

## 4. Distinct Dimensions of Quality
- **Retrieval Correctness**: Measures whether Hindsight retrieved the true historical precedent when one exists, and correctly yielded zero matches for decoys/novel alerts.
- **Evidence Correctness**: Measures whether factual supporting evidence and failed mitigations to avoid were derived strictly from verified postmortems without hallucinating non-existent past incidents.
- **Diagnosis Correctness**: Measures whether the synthesized `likely_root_cause` accurately identifies the underlying failure domain mechanism rather than merely restating symptoms.