# Contributing

IncidentOps Copilot is primarily a competition submission, but the repository is structured so engineering changes remain reviewable.

## Before changing code

1. Read the relevant architecture documentation.
2. Identify whether the change affects memory trust, runbook approval, authentication, or failure handling.
3. Avoid duplicating existing service logic.
4. Keep claims in documentation tied to reproducible evidence.

## Quality gates

Run the relevant checks before opening a pull request:

```bash
ruff check app/
mypy app/
pytest -v
npm run build
```

If dependencies change, also run:

```bash
pip-audit -r requirements.txt
```

## Pull requests

A good PR should explain:

- the problem
- the design decision
- the files changed
- tests executed
- known limitations

Do not add fabricated metrics, fake customer data, or unverifiable performance claims.
