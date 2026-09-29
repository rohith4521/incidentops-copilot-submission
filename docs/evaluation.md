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
- frontend production build and artifact smoke validation
- CodeQL
- pull-request dependency review
- focused security/reliability tests
- memory evaluation and held-out evaluation scripts

## Held-out memory evaluation

The committed evaluation artifact at [../.benchmarks/memory_evaluation.json](../.benchmarks/memory_evaluation.json) records a 20-case synthetic evaluation run with 40 memory-on/off evaluations.

Measured results from that artifact:

| Measure | Result |
|---|---:|
| Relevant-family retrieval | **10/10 (100%)** |
| False retrievals on decoys | **0/5 (0%)** |
| Correct decoy rejection | **5/5 (100%)** |
| Novel-case false matches | **0/5 (0%)** |
| Memory-on historical match rate | **10/10 (100%)** |
| Memory-on verified-runbook availability | **10/10 (100%)** |
| Average memory-on recall latency | **347.5 ms** |
| Average memory-off reasoning latency | **0.37 ms** |

These are **synthetic benchmark results from the committed evaluation harness**, not production measurements. They demonstrate the behavior of the implemented memory/relevance path under the supplied cases; they do not establish production-scale recall quality, latency, or MTTR reduction.

## What the evaluation is intended to demonstrate

### Memory quality

The evaluation harness covers:

- relevant historical recall
- decoy rejection
- novel-case non-match behavior
- memory-enabled vs memory-disabled behavior
- verified-runbook availability
- recall latency

### Diagnosis quality

The project contains dedicated diagnosis-quality benchmarking code rather than relying only on UI screenshots.

### Failure handling

Tests cover Hindsight degradation, circuit-breaker behavior, webhook abuse protection, idempotency, authorization, provenance persistence and prompt-injection defenses.

### Frontend evidence

The frontend CI gate verifies:

1. TypeScript compilation succeeds.
2. A production Vite build succeeds.
3. dist/index.html is present and valid.
4. Referenced JS/CSS assets exist.
5. A production JavaScript bundle is emitted.

This is deliberately described as **artifact validation**, not browser behavior testing.

### Reproducibility

The repository fixes the runtime major/minor versions used by CI and uses `npm ci` with the committed npm lockfile for the frontend.

Python dependencies remain range-based in `requirements.txt`; therefore exact historical Python dependency resolution is **not** claimed yet. This limitation is intentionally explicit rather than hidden.

Evaluation scripts live under [scripts/](../scripts/) and generated reports live under [reports/](../reports/).

## What we do not claim

We do **not** claim:

- a measured percentage reduction in real-world MTTR
- production-scale Hindsight performance
- autonomous production remediation
- perfect security
- independent penetration-test certification
- multi-node high availability
- browser-level accessibility conformance from the artifact smoke test

Those measurements require deployment data and operational validation beyond this submission.

## Evidence rule

Every important claim should map to one of:

**source code → automated test → committed benchmark artifact → CI result → documented limitation**

A visual/demo value that is not measured must be labeled as illustrative rather than presented as telemetry.

## Why this matters

A convincing agent submission should make it possible to distinguish:

**what was implemented → what was tested → what was measured → what remains unverified.**