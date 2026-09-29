## What changed?

<!-- Describe the change in one or two sentences. -->

## Why?

<!-- What problem does this solve? -->

## Scope

- [ ] Backend
- [ ] Frontend
- [ ] Hindsight / memory behavior
- [ ] Security / authorization
- [ ] Evaluation / tests
- [ ] Documentation

## Verification

- [ ] `pytest -v`
- [ ] `ruff check app/`
- [ ] `mypy app/`
- [ ] `npm run build`
- [ ] `pip-audit -r requirements.txt` (if dependencies changed)

## Safety / trust impact

- [ ] Does not weaken human approval boundaries
- [ ] Does not silently promote retrieved memory to trusted evidence
- [ ] Does not fabricate metrics or historical evidence
- [ ] Does not introduce secrets or production credentials

## Evidence

<!-- Add relevant tests, screenshots, reports, or docs. -->

## Limitations

<!-- State any known limitations introduced or exposed by this change. -->
