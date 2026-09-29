"""PHASE 7.4A — Production Secret Fail-Closed Tests.

Validates:
1. When ENVIRONMENT=production and AUTH_JWT_SECRET is the default, startup fails.
2. When ENVIRONMENT=production and AUTH_JWT_SECRET is missing/empty, startup fails.
3. When ENVIRONMENT=production and AUTH_SRE_API_KEYS is the default demo set, startup fails.
4. When ENVIRONMENT=production and AUTH_SRE_API_KEYS contains demo keys, startup fails.
5. When ENVIRONMENT=production and valid custom secrets are supplied, startup succeeds.
6. When ENVIRONMENT is not production (development/demo/test), startup succeeds with defaults.
7. Secret values are NEVER leaked in error messages, exceptions, or logs.
"""

import os
from unittest.mock import patch
import pytest
from pydantic import ValidationError
from starlette.testclient import TestClient

from app.config import (
    DEFAULT_AUTH_JWT_SECRET,
    DEFAULT_AUTH_SRE_API_KEYS,
    Settings,
    settings,
)
from app.main import app


# ---------------------------------------------------------------------------
# Test 1: Production + Default JWT Secret => Startup Failure
# ---------------------------------------------------------------------------

def test_production_default_jwt_secret_fails_startup():
    """Verify that launching in production with the default AUTH_JWT_SECRET fails immediately."""
    # 1. Pydantic Settings instantiation failure
    with pytest.raises((ValueError, ValidationError)) as exc_info:
        Settings(
            environment="production",
            auth_jwt_secret=DEFAULT_AUTH_JWT_SECRET,
            auth_sre_api_keys="prod-custom-key-1:lead-sre-carol",
        )
    err_msg = str(exc_info.value)
    assert "Production configuration error" in err_msg
    assert "default auth_jwt_secret is forbidden" in err_msg.lower()

    # 2. FastAPI Lifespan startup failure
    with patch.object(settings, "environment", "production"):
        with patch.object(settings, "auth_jwt_secret", DEFAULT_AUTH_JWT_SECRET):
            with patch.object(settings, "auth_sre_api_keys", "prod-custom-key-1:lead-sre-carol"):
                with pytest.raises(ValueError) as lifespan_err:
                    with TestClient(app):
                        pass
                assert "Production configuration error" in str(lifespan_err.value)


# ---------------------------------------------------------------------------
# Test 2: Production + Missing/Empty JWT Secret => Startup Failure
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("empty_jwt", ["", "   ", None])
def test_production_missing_jwt_secret_fails_startup(empty_jwt):
    """Verify that launching in production with missing or blank AUTH_JWT_SECRET fails immediately."""
    # 1. Settings validation failure
    with pytest.raises((ValueError, ValidationError)) as exc_info:
        Settings(
            environment="production",
            auth_jwt_secret=empty_jwt,
            auth_sre_api_keys="prod-custom-key-1:lead-sre-carol",
        )
    err_msg = str(exc_info.value)
    assert "Production configuration error" in err_msg
    assert "AUTH_JWT_SECRET must not be empty or missing" in err_msg

    # 2. FastAPI Lifespan startup failure
    with patch.object(settings, "environment", "production"):
        with patch.object(settings, "auth_jwt_secret", empty_jwt):
            with patch.object(settings, "auth_sre_api_keys", "prod-custom-key-1:lead-sre-carol"):
                with pytest.raises(ValueError) as lifespan_err:
                    with TestClient(app):
                        pass
                assert "Production configuration error" in str(lifespan_err.value)


# ---------------------------------------------------------------------------
# Test 3: Production + Default or Demo API Keys => Startup Failure
# ---------------------------------------------------------------------------

def test_production_default_api_keys_fails_startup():
    """Verify that launching in production with default/demo AUTH_SRE_API_KEYS fails immediately."""
    # Exact default string
    with pytest.raises((ValueError, ValidationError)) as exc_info:
        Settings(
            environment="production",
            auth_jwt_secret="strong-random-prod-secret-key-1234567890",
            auth_sre_api_keys=DEFAULT_AUTH_SRE_API_KEYS,
        )
    err_msg = str(exc_info.value)
    assert "Production configuration error" in err_msg
    assert "Default demo AUTH_SRE_API_KEYS are forbidden" in err_msg

    # Individual demo key (sre-key-oncall)
    with pytest.raises((ValueError, ValidationError)) as exc_info2:
        Settings(
            environment="production",
            auth_jwt_secret="strong-random-prod-secret-key-1234567890",
            auth_sre_api_keys="sre-key-oncall:oncall-sre",
        )
    assert "Demo SRE API key identifier is forbidden" in str(exc_info2.value)

    # Empty API keys
    with pytest.raises((ValueError, ValidationError)) as exc_info3:
        Settings(
            environment="production",
            auth_jwt_secret="strong-random-prod-secret-key-1234567890",
            auth_sre_api_keys="",
        )
    assert "AUTH_SRE_API_KEYS must not be empty or missing" in str(exc_info3.value)


# ---------------------------------------------------------------------------
# Test 4: Production + Valid Secrets => Startup Succeeds
# ---------------------------------------------------------------------------

def test_production_valid_secrets_startup_succeeds():
    """Verify that in production with proper non-default credentials, startup succeeds."""
    prod_jwt = "prod-super-secure-unique-jwt-signing-secret-999888"
    prod_keys = "prod-corp-vault-key-1:primary-sre-alice,prod-corp-vault-key-2:oncall-sre-bob"

    # 1. Settings initializes cleanly
    prod_settings = Settings(
        environment="production",
        auth_jwt_secret=prod_jwt,
        auth_sre_api_keys=prod_keys,
    )
    assert prod_settings.environment == "production"
    assert prod_settings.auth_jwt_secret == prod_jwt
    assert prod_settings.auth_sre_api_keys == prod_keys

    # 2. FastAPI Lifespan executes cleanly and serves requests
    with patch.object(settings, "environment", "production"):
        with patch.object(settings, "auth_jwt_secret", prod_jwt):
            with patch.object(settings, "auth_sre_api_keys", prod_keys):
                with TestClient(app) as test_client:
                    resp = test_client.get("/api/v1/health")
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["environment"] == "production"


# ---------------------------------------------------------------------------
# Test 5: Development/Demo Behavior Remains Compatible
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("dev_env", ["development", "test", "demo", "staging"])
def test_development_demo_behavior_remains_compatible(dev_env):
    """Verify that outside of production, default/demo credentials work transparently."""
    dev_settings = Settings(
        environment=dev_env,
        auth_jwt_secret=DEFAULT_AUTH_JWT_SECRET,
        auth_sre_api_keys=DEFAULT_AUTH_SRE_API_KEYS,
    )
    assert dev_settings.environment == dev_env
    # validate_production_secrets() does not raise
    dev_settings.validate_production_secrets()

    # Application starts and serves successfully
    with patch.object(settings, "environment", dev_env):
        with patch.object(settings, "auth_jwt_secret", DEFAULT_AUTH_JWT_SECRET):
            with patch.object(settings, "auth_sre_api_keys", DEFAULT_AUTH_SRE_API_KEYS):
                with TestClient(app) as test_client:
                    resp = test_client.get("/api/v1/health")
                    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Test 6: Secrets Are Never Logged or Leaked in Exceptions
# ---------------------------------------------------------------------------

def test_secrets_are_never_logged_or_leaked_in_exceptions():
    """Verify that secret values are strictly excluded from error messages."""
    canary_jwt_secret = "CANARY_SECRET_JWT_DO_NOT_LEAK_7777777"
    demo_keys = DEFAULT_AUTH_SRE_API_KEYS

    with pytest.raises((ValueError, ValidationError)) as exc_info:
        Settings(
            environment="production",
            auth_jwt_secret=canary_jwt_secret,
            auth_sre_api_keys=demo_keys,
        )

    error_text = str(exc_info.value)
    # The error must mention the policy violation
    assert "Production configuration error" in error_text
    # The error must NEVER contain the secret value
    assert canary_jwt_secret not in error_text
