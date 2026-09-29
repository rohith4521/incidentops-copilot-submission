# CI and Supply-Chain Security

IncidentOps Copilot treats CI as part of the security boundary.

## Required gates

Every change to the protected development path is expected to pass:

- Python linting with Ruff
- Python static typing with Mypy
- Python dependency auditing with pip-audit
- Full pytest suite
- Frontend TypeScript/Vite production build
- npm dependency audit
- CodeQL analysis
- Pull-request dependency review
- Docker image build validation

## Workflow hardening

GitHub Actions workflows use:

- explicit least-privilege workflow permissions
- concurrency cancellation to prevent stale duplicate runs
- job timeouts to bound runaway execution
- immutable SHA pinning for selected high-impact actions
- Dependabot updates for Python, npm and GitHub Actions dependencies

GitHub recommends pinning third-party actions to full-length commit SHAs because a SHA is an immutable release reference. See the repository security documentation for the rationale.

## Local equivalent

Run the complete local quality path with:

```bash
make ci
```

Or run individual gates:

```bash
make lint
make typecheck
make audit
make test
make build
make docker
```

## Deliberate limits

This repository does not claim that CI alone makes the application production-secure. Runtime security, deployment configuration, secrets management, infrastructure controls and GitHub repository settings remain separate responsibilities.
