# Judge Audit Guide

This page maps important README claims to concrete repository evidence.

## 1. Hindsight is central

Inspect the memory services, continuous-learning tests, memory evaluation tests and docs/memory-model.md.

## 2. Retrieval is not trusted automatically

Inspect failure-mode relevance tests, provenance/trust tests and assets/trust-gate.svg.

## 3. The system learns

Inspect continuous-learning tests, retention/provenance protection tests and demo/evaluation scripts.

## 4. The system fails honestly

Inspect circuit-breaker/degradation implementation, resilience tests and docs/architecture.md.

## 5. Remediation is bounded

Inspect runbook/approval services, authorization tests, docs/security.md and docs/threat-model.md.

## 6. Engineering quality is measurable

Repository evidence includes 232 passed, 1 skipped, 0 failures at the documented verification point; Ruff; Mypy; pip-audit; Docker build validation; frontend TypeScript/Vite production build CI; and dedicated security, reliability and evaluation tests.

## 7. What is not claimed

Do not infer from the repository:
- real-world MTTR improvement
- production-scale Hindsight throughput
- autonomous production remediation
- perfect prompt-injection prevention
- globally distributed high availability
- cryptographic immutability or hardware-enclave security

The project is evaluated on demonstrated implementation rather than unsupported marketing claims.
