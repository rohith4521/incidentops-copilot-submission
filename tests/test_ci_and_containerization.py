"""Phase 6.9A Focused Tests: CI Pipeline and Container Deployment Validation.

Verifies:
1. Dockerfile exists, uses Python 3.11, non-root user, and references the correct entrypoint (app.main:app).
2. Dockerfile provides configurable HOST/PORT and includes container healthcheck targeting existing health endpoint.
3. .dockerignore exists and excludes secrets (.env), test suites, git metadata, and ephemeral caches.
4. GitHub Actions CI workflow exists, triggers on push/pull_request, sets up Python 3.11, installs requirements.txt, and runs pytest.
5. docker-compose.yml defines both IncidentOps API and Hindsight services with persistent volume and port mapping.
6. No secrets, credentials, or API keys are hardcoded in Docker, Compose, or CI configurations.
"""

from pathlib import Path
import re
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_1_dockerfile_configuration_and_entrypoint():
    """Verify Dockerfile exists and references the correct application entrypoint."""
    dockerfile_path = REPO_ROOT / "Dockerfile"
    assert dockerfile_path.exists(), "Dockerfile must exist at repository root"

    content = dockerfile_path.read_text(encoding="utf-8")

    # Base image check
    assert "python:3.11" in content or "FROM python:3.11" in content

    # Application entrypoint check
    assert "app.main:app" in content, "Dockerfile must reference app.main:app entrypoint"
    assert "uvicorn" in content, "Dockerfile must use uvicorn to run FastAPI app"

    # Non-root user check
    assert "useradd" in content or "adduser" in content, "Dockerfile must create a non-root user"
    assert "USER appuser" in content or re.search(r"USER\s+\w+", content), "Dockerfile must switch to a non-root user"


def test_2_dockerfile_host_port_and_healthcheck():
    """Verify Dockerfile configures HOST/PORT and includes container healthcheck."""
    dockerfile_path = REPO_ROOT / "Dockerfile"
    content = dockerfile_path.read_text(encoding="utf-8")

    # Host and port configuration
    assert "HOST" in content and "PORT" in content
    assert "EXPOSE" in content

    # Healthcheck directive targeting the existing health endpoint
    assert "HEALTHCHECK" in content
    assert "/api/v1/health" in content or "/api/health" in content


def test_3_dockerignore_excludes_sensitive_files():
    """Verify .dockerignore exists and excludes secrets, tests, caches, and git files."""
    dockerignore_path = REPO_ROOT / ".dockerignore"
    assert dockerignore_path.exists(), ".dockerignore must exist at repository root"

    content = dockerignore_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]

    expected_exclusions = [".env", "tests/", ".git/", ".pytest_cache/"]
    for expected in expected_exclusions:
        assert any(expected in line for line in lines), f".dockerignore must exclude {expected}"


def test_4_ci_workflow_specification():
    """Verify GitHub Actions CI workflow triggers on push/PR, uses Python 3.11, and runs pytest."""
    ci_path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
    assert ci_path.exists(), "GitHub Actions workflow .github/workflows/ci.yml must exist"

    content = ci_path.read_text(encoding="utf-8")
    ci_config = yaml.safe_load(content)

    # Check triggers
    # In yaml, True is parsed from 'on' if not quoted or 'on' mapping
    triggers = ci_config.get("on") or ci_config.get(True)
    assert triggers is not None
    assert "push" in triggers
    assert "pull_request" in triggers

    # Check jobs
    assert "jobs" in ci_config
    assert "test" in ci_config["jobs"]

    job = ci_config["jobs"]["test"]
    job_str = str(job)

    # Python 3.11 check
    assert "3.11" in job_str

    # Requirements installation check
    assert "requirements.txt" in job_str

    # Pytest execution check
    assert "pytest" in job_str


def test_5_docker_compose_architecture():
    """Verify docker-compose.yml configures API and Hindsight services with volume and ports."""
    compose_path = REPO_ROOT / "docker-compose.yml"
    assert compose_path.exists(), "docker-compose.yml must exist at repository root"

    content = compose_path.read_text(encoding="utf-8")
    compose_config = yaml.safe_load(content)

    assert "services" in compose_config
    services = compose_config["services"]

    # API service check
    assert "api" in services
    api_svc = services["api"]
    assert "build" in api_svc
    assert "ports" in api_svc
    assert any("8000" in str(p) for p in api_svc["ports"])
    assert "depends_on" in api_svc
    assert "hindsight" in api_svc["depends_on"]

    # Hindsight service check
    assert "hindsight" in services
    hindsight_svc = services["hindsight"]
    assert "ports" in hindsight_svc
    assert any("8888" in str(p) for p in hindsight_svc["ports"])
    assert "volumes" in hindsight_svc

    # Named volume check
    assert "volumes" in compose_config
    assert "hindsight_data" in compose_config["volumes"]


def test_6_no_embedded_secrets_in_docker_and_compose():
    """Verify no hardcoded credentials or API keys exist in Docker, Compose, or CI files."""
    files_to_check = [
        REPO_ROOT / "Dockerfile",
        REPO_ROOT / "docker-compose.yml",
        REPO_ROOT / ".github" / "workflows" / "ci.yml",
    ]

    secret_indicators = [
        re.compile(r"gsk_[a-zA-Z0-9_\-]{20,}"),
        re.compile(r"-----BEGIN (?:RSA )?PRIVATE KEY-----"),
    ]

    for file_path in files_to_check:
        text = file_path.read_text(encoding="utf-8")
        for pattern in secret_indicators:
            assert not pattern.search(text), f"Found potential secret match in {file_path.name}"

    # Also verify docker-compose env vars use parameterized expansion ${VAR:-...}
    compose_text = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "${GROQ_API_KEY" in compose_text or "GROQ_API_KEY: ''" in compose_text
    assert "${HINDSIGHT_API_KEY" in compose_text or "HINDSIGHT_API_KEY: ''" in compose_text


def test_7_requirements_definition_includes_core_and_test():
    """Verify requirements.txt defines all runtime and testing dependencies."""
    req_path = REPO_ROOT / "requirements.txt"
    assert req_path.exists()
    content = req_path.read_text(encoding="utf-8").lower()

    essential_pkgs = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "groq",
        "hindsight-client",
        "pytest",
        "pytest-asyncio",
        "pyjwt",
    ]
    for pkg in essential_pkgs:
        assert pkg in content, f"Package {pkg} must be listed in requirements.txt"
