# Security & Trust

IncidentOps Copilot treats incident automation as a **human-gated reliability system**, not an unrestricted command executor.

## Controls

### Authentication and authorization

Sensitive API surfaces are protected by the application's authentication and authorization layers. Runbook actions require an explicit approval state.

### Human approval

Recommended runbooks begin in a pending state. Simulation/execution is not treated as an implicit consequence of model output.

### Prompt-injection resistance

Untrusted incident content is treated as data rather than trusted instructions. The system includes defensive checks around prompt-injection patterns and preserves a separation between operational evidence and model instructions.

### Memory provenance

Historical memory is not accepted solely because it was retrieved. Provenance and relevance checks are part of the trust pipeline.

### Failure containment

Hindsight failures, authentication failures, timeouts and rate-limit conditions are handled explicitly so the application does not invent historical evidence.

### Secrets

Runtime credentials belong in environment variables. `.env` files are ignored by Git. CI uses test-only fixture values rather than production credentials.

## Scope and limitations

This is a hackathon-grade system, not a claim of universal production security. Known limitations include process-local rate limiting, single-node persistence choices, heuristic prompt-injection defenses and the absence of production-scale operational evidence.

The correct security claim is therefore:

> **The system is deliberately designed with multiple safety boundaries and tested failure modes; it does not claim that those boundaries are perfect.**
