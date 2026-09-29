# Hindsight Memory Model

## Why memory is the product

A stateless incident assistant can explain an alert. IncidentOps Copilot is designed to answer a harder question:

> **Have we seen this failure mode before, what did we learn, and can we trust that memory now?**

## Memory lifecycle

1. **Recall** historical candidates from Hindsight.
2. **Compare** the current failure mode and operational context.
3. **Reject** weak or misleading candidates.
4. **Promote** evidence-backed candidates to trusted context.
5. **Diagnose** using the current incident plus trusted evidence.
6. **Recommend** a runbook with a human approval boundary.
7. **Resolve** and record the outcome.
8. **Retain** a structured postmortem for future incidents.

## Incident states

### Known

A relevant verified memory exists.

```text
current alert
   ↓
historical match
   ↓
verified evidence
   ↓
diagnosis
   ↓
runbook
```

### Novel

No sufficiently relevant historical incident is found.

```text
current alert
   ↓
no trusted precedent
   ↓
fresh investigation
   ↓
human verification
   ↓
postmortem retained
```

The next occurrence can then become a known incident.

### Decoy

A candidate is retrieved but fails contextual relevance or provenance checks.

The candidate remains inspectable in the trace while being excluded from trusted evidence.

### Degraded

Hindsight is unavailable or unhealthy.

The system does not manufacture a successful recall. It explicitly enters degraded behavior.

## Trust language

Use these terms precisely:

- **Retrieved:** returned by memory search.
- **Relevant:** matches the current failure mode/context.
- **Trusted:** passed evidence/provenance checks.
- **Verified:** operational outcome has been confirmed and retained.

These are deliberately different states.
