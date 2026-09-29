PYTHON ?= python
PIP ?= pip
NPM ?= npm

.PHONY: install test lint typecheck audit build frontend ci docker

install:
	$(PIP) install -r requirements.txt
	$(PIP) install ruff mypy pip-audit
	$(NPM) ci

test:
	pytest -v

lint:
	ruff check app/

typecheck:
	mypy app/

audit:
	pip-audit -r requirements.txt
	$(NPM) audit --audit-level=high

build:
	$(NPM) run build

frontend:
	$(NPM) run dev

docker:
	docker build --pull -t incidentops-copilot:local .

ci: lint typecheck audit test build
