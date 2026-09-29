# Reproducibility Guide

## Goal

A reviewer should be able to understand how the system is built, tested and evaluated without relying on undocumented local state.

## Backend

    cp .env.example .env
    pip install -r requirements.txt
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
    pytest -v
    ruff check app/
    mypy app/
    pip-audit -r requirements.txt

## Frontend

    npm ci
    npm run build

## Demo and evaluation

The scripts directory contains utilities for seeding memory and exercising representative alert scenarios. Evaluation documentation distinguishes reproducible engineering checks from illustrative demo flows.

## Configuration discipline

Never commit real secrets. CI uses test-only credentials and mock/fake external configuration where appropriate. Production credentials belong in deployment secret stores.

## Evidence discipline

Reported numbers must be traceable to a test, benchmark or deployment measurement. Illustrative UI telemetry must not be presented as measured production performance.
