# Evaluation & Evidence

## Engineering verification

The current backend verification result is:

- **232 passed**
- **1 skipped**
- **0 failures**

Additional quality gates include:

- Ruff
- Mypy
- dependency audit
- Docker build
- focused security/reliability tests
- memory evaluation and held-out evaluation scripts

## What the evaluation is intended to demonstrate

### Memory quality

The evaluation harness covers recall, relevance, multi-incident learning and held-out behavior.

### Diagnosis quality

The project contains dedicated diagnosis-quality benchmarking code rather than relying only on UI screenshots.

### Failure handling

Tests cover Hindsight degradation, circuit-breaker behavior, webhook abuse protection, idempotency, authorization, provenance persistence and prompt-injection defenses.

### Reproducibility

Evaluation scripts live under [scripts/](../scripts/) and generated reports live under [reports/](../reports/).

## What we do not claim

We do **not** claim a measured percentage reduction in real-world MTTR, production-scale Hindsight performance, autonomous production remediation, or perfect security.

Those measurements require deployment data and operational validation beyond this submission.

## Why this matters

A convincing agent submission should make it possible to distinguish:

**what was implemented → what was tested → what was measured → what remains unverified.**
