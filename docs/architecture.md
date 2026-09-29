# Architecture

IncidentOps Copilot is an SRE incident-response system built around one central idea: **operational memory should be reusable, inspectable, and gated by evidence**.

## Runtime flow

```text
Alert / Webhook / UI
        |
        v
  FastAPI ingestion
        |
        +--------------------+
        |                    |
        v                    v
 Hindsight recall       LLM reasoning
        |                    |
        +---------+----------+
                  v
          Relevance gate
                  |
        +---------+---------+
        |                   |
      reject              accept
        |                   |
     decoy              trusted evidence
                            |
                            v
                     diagnosis + runbook
                            |
                     human approval
                            |
                  dry-run / controlled action
                            |
                            v
                       postmortem
                            |
                            v
                    Hindsight retain
                            |
                            +----> future recall
```

## Components

| Component | Responsibility |
|---|---|
| FastAPI | API surface, orchestration and validation |
| Hindsight | Persistent incident recall, retention and reflection |
| LLM layer | Diagnosis synthesis and reasoning |
| Relevance/trust layer | Failure-mode-aware filtering and provenance checks |
| Runbook service | Human approval boundary and simulation |
| Frontend | Command Center, spatial memory and trace audit |
| CI | Ruff, mypy, pip-audit, pytest and Docker build |

## Design principle

The system intentionally separates:

**Retrieved → Relevant → Trusted → Verified**

A memory candidate is not treated as operational truth simply because a retrieval system returned it.

## Failure behavior

If Hindsight is unavailable, the application degrades rather than fabricating historical evidence. Novel incidents can still receive first-principles reasoning and become candidates for a future verified postmortem.

See [memory-model.md](memory-model.md) and [security.md](security.md).
