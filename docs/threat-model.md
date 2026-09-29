# Threat Model

## Scope

IncidentOps Copilot is an incident-response assistant. It consumes alerts, historical operational memory, model output and runbook metadata. Historical memory can inform diagnosis without becoming unquestioned authority.

## Assets

| Asset | Why it matters |
|---|---|
| Incident data | May contain operationally sensitive information |
| Hindsight memories | Historical evidence used for future diagnosis |
| Provenance metadata | Establishes where trusted evidence came from |
| Runbook definitions | Describe operational actions |
| Credentials and API keys | Protect external integrations |
| Approval state | Prevents recommendations from silently becoming actions |

## Trust boundaries

1. External alert source -> API: untrusted input.
2. API -> memory layer: retrieved data is candidate evidence.
3. Memory -> relevance/trust gate: candidates are evaluated before entering trusted context.
4. LLM -> application: generated diagnosis is untrusted output.
5. Diagnosis -> runbook approval: human approval remains a control boundary.
6. Application -> external systems: integrations must authenticate and validate inputs.

## Threats and mitigations

| Threat | Mitigation |
|---|---|
| Prompt injection in incident content | Input handling and heuristic prompt-injection defenses |
| False historical grounding | Relevance gate and provenance/trust checks |
| Direct unauthorized memory writes | Protected retention paths and authorization |
| Duplicate webhook delivery | Persisted webhook idempotency |
| Hindsight outage | Circuit-breaker/degraded behavior; no fabricated recall |
| Unauthorized API access | Authentication and authorization |
| Proxy/IP spoofing | Trusted-proxy configuration |
| Unsafe remediation | Human approval boundary |
| Cross-origin abuse | Explicit CORS configuration |
| Secret leakage | Production-secret fail-closed behavior and test fixtures |
| Dependency vulnerabilities | pip-audit CI gate |

## Residual risk

This is a hackathon-grade security model. Prompt-injection defenses are heuristic rather than complete, deployment topology is not a globally distributed production architecture, and no security claim is a guarantee.

## Security verification

Dedicated tests cover authentication, memory-retention protection, webhook abuse/idempotency, proxy/CORS hardening, prompt-injection defenses, and degraded-memory behavior.
