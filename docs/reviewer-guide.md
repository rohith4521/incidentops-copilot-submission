# Reviewer Guide

## What this repository is proving

IncidentOps Copilot demonstrates a specific engineering thesis:

> Incident response becomes more useful when verified incident history is treated as operational memory rather than one-shot prompt context.

The repository is intentionally scoped around that loop.

## 90-second evaluation path

1. **Open the live product**  
   https://incidentops-copilot.vercel.app

2. **Trigger or inspect a known incident**  
   Follow the incident trace from alert → Hindsight recall → relevance → evidence → diagnosis → runbook → approval.

3. **Inspect the memory distinction**  
   Look for the separation between:
   - Retrieved
   - Relevant
   - Trusted
   - Verified

4. **Inspect the novel-incident path**  
   A novel scenario should not manufacture a historical precedent. It should fall back to fresh reasoning and create a candidate postmortem for future memory.

5. **Inspect the degraded path**  
   Hindsight failures should be visible as degraded behavior rather than represented as successful recall.

6. **Inspect the code evidence**  
   Start with:
   - [Architecture](architecture.md)
   - [Memory model](memory-model.md)
   - [Security](security.md)
   - [Evaluation](evaluation.md)
   - [Decision records](decision-records.md)

## The technical differentiator

The project does not treat retrieval as truth.

A candidate returned by memory can be rejected when its failure mode or context is not sufficiently relevant. Trusted evidence is then separated from raw candidates before diagnosis synthesis.

That distinction is central to the implementation and to the UI.

## Evidence over claims

The repository reports a verification snapshot of:

**232 passed · 1 skipped · 0 failures**

It also deliberately avoids claiming measured real-world MTTR reduction, production-scale Hindsight performance, autonomous production remediation, universal HA, or perfect prompt-injection prevention.

Those omissions are intentional: they mark the boundary between demonstrated behavior and future production validation.

## Architecture at a glance

```text
Alert
  │
  ▼
FastAPI triage
  │
  ├──────────────► LLM synthesis
  │
  ▼
Hindsight recall
  │
  ▼
Relevance / trust gate
  │
  ▼
Evidence-backed diagnosis
  │
  ▼
Runbook recommendation
  │
  ▼
Human approval
  │
  ▼
Resolution / simulation
  │
  ▼
Postmortem retention
  │
  └──────────────► future Hindsight recall
```

## If you only inspect one concept

Inspect the transition:

**Retrieved → Relevant → Trusted → Verified**

That is the core product boundary.
