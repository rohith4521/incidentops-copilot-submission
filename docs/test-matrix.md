# Verification Matrix

The test suite is organized around product failure boundaries rather than only happy-path API responses.

| Area | What is verified |
|---|---|
| API routing | Canonical endpoints and route behavior |
| Authentication | Protected API access and identity handling |
| Authorization | Role/runbook approval boundaries |
| Hindsight integration | Recall/retain behavior and degraded operation |
| Memory relevance | Failure-mode-aware candidate filtering |
| Memory trust | Provenance and retention protections |
| Continuous learning | Incident -> postmortem -> future recall loop |
| Diagnosis quality | Benchmark and decoy cases |
| Webhooks | Alertmanager ingestion, validation and idempotency |
| Resilience | Circuit-breaker and dependency failure behavior |
| Security hardening | CORS, trusted proxy, secret handling and prompt injection |
| Persistence | Docker/API persistence checks |
| Evaluation | Held-out/evaluation harness behavior |
| Packaging | Docker build and CI configuration |

## Evidence

Run:

    pytest -v
    ruff check app/
    mypy app/
    pip-audit -r requirements.txt
    npm ci
    npm run build

The frontend production build is enforced by `.github/workflows/frontend.yml`.

## Interpretation

A passing test means coded behavior matched the test contract. It does not imply production-scale reliability, security perfection, or real-world MTTR reduction.
