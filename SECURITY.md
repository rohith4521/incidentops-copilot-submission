# Security Policy

## Scope

IncidentOps Copilot is a hackathon project demonstrating evidence-gated SRE incident assistance.

## Reporting

Please do not disclose sensitive credentials, API keys, private incident data, or exploit details in public issues.

For a security concern, open a private security report through the repository's GitHub security interface when available, or contact the repository owner directly.

## Security design

The implementation includes authentication/authorization boundaries, prompt-injection defenses, provenance checks, webhook abuse protection, idempotency, circuit-breaker behavior, and human approval before controlled runbook actions.

## Important limitation

These controls are not a guarantee of perfect security. The project has not undergone an independent penetration test or production-scale security audit.

## Secrets

Never commit:

- `.env`
- API keys
- access tokens
- private certificates
- production incident data

Use `.env.example` as the configuration template.
