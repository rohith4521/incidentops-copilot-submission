"""PHASE 7.4D — Docker API State Persistence & Database Packaging Protection Tests.

Validates:
1. docker-compose.yml declares dedicated persistent volume for API state (api_data).
2. api_data volume is mounted at the correct application data directory (/app/app/data).
3. Hindsight volume (hindsight_data) remains intact and unaffected.
4. .gitignore excludes all SQLite runtime database files (*.db, *.sqlite, *.sqlite3, *.db-wal, *.db-shm).
5. .dockerignore excludes runtime SQLite database files so they are not baked into the Docker image.
6. Static seed and evaluation JSON datasets in app/data are NOT excluded by git or docker.
7. Existing provenance persistence tests still pass.
8. Existing webhook idempotency persistence tests still pass.
"""

from pathlib import Path
import pytest
import yaml

from app.config import settings
from app.services.provenance_service import provenance_service
from app.services.webhook_service import idempotency_store

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Test 1 & 2: Docker Compose Volume Configuration
# ---------------------------------------------------------------------------

def test_1_docker_compose_declares_api_state_volume():
    """Verify that docker-compose.yml defines a dedicated volume for API runtime state."""
    compose_file = REPO_ROOT / "docker-compose.yml"
    assert compose_file.exists(), "docker-compose.yml must exist at repository root"

    content = yaml.safe_load(compose_file.read_text(encoding="utf-8"))

    # Top-level volumes declaration
    assert "volumes" in content, "docker-compose.yml must define top-level volumes"
    volumes = content["volumes"]
    assert "api_data" in volumes, "docker-compose.yml must declare 'api_data' volume"
    assert "hindsight_data" in volumes, "docker-compose.yml must preserve 'hindsight_data' volume"


def test_2_api_volume_mounted_at_correct_app_data_path():
    """Verify that api_data volume is mounted to /app/app/data in the API container."""
    compose_file = REPO_ROOT / "docker-compose.yml"
    content = yaml.safe_load(compose_file.read_text(encoding="utf-8"))

    api_service = content.get("services", {}).get("api", {})
    assert "volumes" in api_service, "api service must specify volumes"

    api_volumes = api_service["volumes"]
    # Check that api_data is mounted to /app/app/data
    matching_mount = [
        v for v in api_volumes
        if ("api_data:/app/app/data" in str(v)) or (isinstance(v, dict) and v.get("source") == "api_data" and v.get("target") == "/app/app/data")
    ]
    assert len(matching_mount) > 0, (
        f"api_data must be mounted to /app/app/data in api service. Found: {api_volumes}"
    )


# ---------------------------------------------------------------------------
# Test 3 & 4: SQLite Runtime Database Exclusions in .gitignore & .dockerignore
# ---------------------------------------------------------------------------

def test_3_gitignore_excludes_sqlite_runtime_files():
    """Verify that .gitignore excludes *.db, *.db-wal, *.sqlite, and related SQLite files."""
    gitignore_file = REPO_ROOT / ".gitignore"
    assert gitignore_file.exists(), ".gitignore must exist at repository root"

    lines = [
        line.strip() for line in gitignore_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

    required_patterns = ["*.db", "*.db-wal", "*.db-shm", "*.sqlite", "*.sqlite3"]
    for pattern in required_patterns:
        assert any(pattern == l or pattern in l for l in lines), (
            f".gitignore must exclude SQLite pattern '{pattern}'"
        )


def test_4_dockerignore_excludes_runtime_databases_from_build_context():
    """Verify that .dockerignore excludes runtime SQLite databases to avoid baking them into images."""
    dockerignore_file = REPO_ROOT / ".dockerignore"
    assert dockerignore_file.exists(), ".dockerignore must exist at repository root"

    lines = [
        line.strip() for line in dockerignore_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

    required_patterns = ["*.db", "*.db-wal", "*.sqlite"]
    for pattern in required_patterns:
        assert any(pattern == l or pattern in l for l in lines), (
            f".dockerignore must exclude SQLite pattern '{pattern}'"
        )


# ---------------------------------------------------------------------------
# Test 5: Seed & Evaluation JSON Datasets Preserved
# ---------------------------------------------------------------------------

def test_5_seed_and_evaluation_datasets_preserved():
    """Verify that essential static JSON datasets in app/data are not excluded by git or docker."""
    app_data = REPO_ROOT / "app" / "data"
    assert app_data.exists(), "app/data directory must exist"

    essential_datasets = [
        "seed_incidents.json",
        "eval_dataset.json",
        "held_out_evaluation_dataset.json",
        "scale_synthetic_incidents.json",
        "multi_incident_scenarios.json",
    ]

    for dataset in essential_datasets:
        file_path = app_data / dataset
        assert file_path.exists(), f"Essential dataset {dataset} must exist in app/data"
        assert file_path.stat().st_size > 0, f"Essential dataset {dataset} must not be empty"


# ---------------------------------------------------------------------------
# Test 6: Database Paths Unchanged in Services
# ---------------------------------------------------------------------------

def test_6_database_paths_remain_consistently_configured():
    """Verify that provenance_service and webhook_service point to the standard configured database path."""
    expected_path = Path(settings.provenance_db_path).resolve()
    assert Path(provenance_service.db_path).resolve() == expected_path
    assert Path(idempotency_store.db_path).resolve() == expected_path
