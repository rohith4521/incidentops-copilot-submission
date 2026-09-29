# Demo Guide

The fastest way to understand IncidentOps Copilot is to demonstrate the **memory loop**, not simply the dashboard.

## 1. Establish the problem

Start with a fresh incident and show the current alert context.

## 2. Show recall

Open the Hindsight memory trace and distinguish:

- raw candidates
- rejected candidates
- trusted evidence
- verified memory

## 3. Show diagnosis

Explain how the current incident is combined with trusted historical evidence.

## 4. Show the safety boundary

Open the recommended runbook and demonstrate that approval is explicit.

## 5. Show continuous learning

For a novel incident:

```text
No trusted precedent
      ↓
Fresh investigation
      ↓
Human verification
      ↓
Postmortem retained
      ↓
Future recall
```

## The key sentence

> The important demo is not that the agent can answer an alert. It is that the answer can become verified operational memory and influence the next incident.

## Demo honesty

Do not present simulated incidents as live production incidents. Label demo data as demo data.
