PYTHON ?= python
PIP ?= pip
NPM ?= npm

.PHONY: install test coverage lint typecheck audit build frontend smoke credibility-smoke docker ci

install:
	$(PIP) install -r requirements.txt
	$(PIP) install ruff mypy pip-audit
	$(NPM) ci

test:
	pytest -v

coverage:
	pytest -v --cov=app --cov-report=term-missing --cov-report=xml

lint:
	ruff check app/

typecheck:
	mypy app/

audit:
	pip-audit -r requirements.txt
	$(NPM) audit --audit-level=high

build:
	$(NPM) run build

smoke:
	node scripts/frontend-smoke.mjs

credibility-smoke:
	node scripts/frontend-credibility-smoke.mjs

frontend:
	$(NPM) run dev

docker:
	docker build --pull -t incidentops-copilot:local .

ci: lint typecheck audit coverage build smoke credibility-smoke docker
