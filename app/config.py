"""Application configuration management via Pydantic BaseSettings."""

from typing import List, Optional
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_AUTH_JWT_SECRET = "incidentops-sre-verified-jwt-secret-key-prod-2026"
DEFAULT_AUTH_SRE_API_KEYS = "sre-key-alice:lead-sre-alice,sre-key-oncall:oncall-sre,sre-key-admin:admin-sre"
DEMO_SRE_API_KEYS = {"sre-key-alice", "sre-key-oncall", "sre-key-admin"}


class Settings(BaseSettings):
    # Hindsight Memory Engine Configuration
    hindsight_api_url: str = Field(
        default="https://api.hindsight.vectorize.io",
        description="Base URL for Hindsight Cloud or self-hosted Hindsight API",
    )
    hindsight_api_key: Optional[str] = Field(
        default=None,
        description="API key for Hindsight Cloud (optional for local unauthenticated instances)",
    )
    hindsight_bank_id: str = Field(
        default="sre-incidentops-production",
        description="Hindsight memory bank identifier for SRE incident memory",
    )
    hindsight_timeout_seconds: float = Field(
        default=30.0,
        description="Timeout in seconds for Hindsight API calls",
    )
    # Hindsight Circuit Breaker Configuration (Phase 7.6)
    hindsight_cb_failure_threshold: int = Field(
        default=3,
        description="Consecutive failure count to trip Hindsight circuit breaker from CLOSED to OPEN",
    )
    hindsight_cb_recovery_timeout_seconds: float = Field(
        default=30.0,
        description="Duration in seconds the circuit breaker remains OPEN before allowing a single HALF_OPEN probe",
    )
    hindsight_cb_request_timeout_seconds: float = Field(
        default=10.0,
        description="Request timeout in seconds for Hindsight dependency API calls guarded by circuit breaker",
    )

    # Groq Inference Configuration
    groq_api_key: Optional[str] = Field(
        default=None,
        description="API key for Groq inference",
    )
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq model ID (e.g. llama-3.3-70b-versatile, qwen-2.5-32b)",
    )

    # LLM Reliability & Resilience Configuration (Phase 6.1)
    llm_timeout_seconds: float = Field(
        default=15.0,
        description="Timeout in seconds for LLM provider API requests",
    )
    llm_max_retries: int = Field(
        default=2,
        description="Maximum bounded retries for transient LLM provider failures",
    )
    llm_retry_initial_delay_seconds: float = Field(
        default=0.2,
        description="Initial delay in seconds for exponential backoff retry",
    )
    fallback_llm_provider: Optional[str] = Field(
        default="mock",
        description="Fallback provider identifier when primary LLM is unavailable (e.g. 'mock', 'secondary')",
    )

    # Provenance Authentication Configuration (Phase 6.3A)
    auth_jwt_secret: Optional[str] = Field(
        default=DEFAULT_AUTH_JWT_SECRET,
        description="Secret key for signing and verifying SRE verification JWTs",
    )
    auth_jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm",
    )
    auth_sre_api_keys: Optional[str] = Field(
        default=DEFAULT_AUTH_SRE_API_KEYS,
        description="Comma-separated key:identity pairs for SRE API-key authentication",
    )

    # Provenance Audit Database Configuration (Phase 7.3A)
    provenance_db_path: str = Field(
        default="app/data/provenance_audit.db",
        description="Path to SQLite database for durable provenance verification audit records",
    )

    # Webhook Idempotency Database Configuration (Phase 7.3B)
    webhook_db_path: str = Field(
        default="app/data/provenance_audit.db",
        description="Path to SQLite database for durable Alertmanager webhook idempotency records",
    )

    # Webhook Abuse Protection & Rate Limiting Configuration (Phase 7.4E)
    webhook_max_body_bytes: int = Field(
        default=256 * 1024,
        description="Maximum allowed webhook request payload size in bytes (default 256 KB)",
    )
    webhook_max_alerts_count: int = Field(
        default=50,
        description="Maximum number of alerts allowed in a single Alertmanager webhook payload batch",
    )
    webhook_max_field_len: int = Field(
        default=8192,
        description="Maximum allowed character length for any individual label or annotation value",
    )
    webhook_rate_limit_requests: int = Field(
        default=60,
        description="Process-local rate limit: maximum allowed novel triage requests per window",
    )
    webhook_rate_limit_window_seconds: int = Field(
        default=60,
        description="Process-local rate limit: window duration in seconds",
    )
    webhook_rate_limit_enabled: bool = Field(
        default=True,
        description="Enable or disable process-local webhook rate limiting",
    )

    # Server Configuration
    host: str = Field(default="127.0.0.1", description="FastAPI host binding")
    port: int = Field(default=8000, description="FastAPI port binding")
    environment: str = Field(default="development", description="Runtime environment")
    log_level: str = Field(default="INFO", description="Logging level")

    # CORS Configuration (Phase 7.8)
    cors_allowed_origins: str = Field(
        default="http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000",
        description="Comma-separated list of allowed CORS origins or '*' for wildcard",
    )

    # Trusted Proxies Configuration (Phase 7.8)
    trusted_proxies: str = Field(
        default="127.0.0.1,::1,testclient",
        description="Comma-separated list of trusted proxy IP addresses or hostnames allowed to forward client IPs",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_hindsight_configured(self) -> bool:
        """Returns True if Hindsight can be addressed (local URL or Cloud with key)."""
        if "localhost" in self.hindsight_api_url or "127.0.0.1" in self.hindsight_api_url:
            return True
        return bool(self.hindsight_api_key and self.hindsight_api_key.strip())

    @property
    def is_groq_configured(self) -> bool:
        """Returns True if Groq API key is present."""
        return bool(self.groq_api_key and self.groq_api_key.strip())

    @property
    def cors_origins_list(self) -> List[str]:
        """Return parsed list of CORS origins."""
        raw = (self.cors_allowed_origins or "").strip()
        if not raw:
            return ["http://localhost:8000", "http://127.0.0.1:8000"]
        if raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def trusted_proxies_list(self) -> List[str]:
        """Return parsed list of trusted proxy IPs/hostnames."""
        raw = (self.trusted_proxies or "").strip()
        if not raw:
            return ["127.0.0.1", "::1", "testclient"]
        return [p.strip() for p in raw.split(",") if p.strip()]

    def validate_production_secrets(self) -> "Settings":
        """Enforce fail-closed secret validation when running in production (Phase 7.4A).

        Rejects default, missing, or demo authentication credentials when ENVIRONMENT=production.
        Never formats or reveals the actual secret values in error messages or logs.
        """
        env = (self.environment or "").strip().lower()
        if env == "production":
            # 1. Reject empty or missing AUTH_JWT_SECRET
            jwt_sec = (self.auth_jwt_secret or "").strip()
            if not jwt_sec:
                raise ValueError(
                    "Production configuration error: AUTH_JWT_SECRET must not be empty or missing when ENVIRONMENT=production."
                )

            # 2. Reject known default AUTH_JWT_SECRET
            if jwt_sec == DEFAULT_AUTH_JWT_SECRET:
                raise ValueError(
                    "Production configuration error: Known default AUTH_JWT_SECRET is forbidden when ENVIRONMENT=production. "
                    "A secure, non-default JWT secret must be provided."
                )

            # 3. Reject empty or missing AUTH_SRE_API_KEYS
            keys_raw = (self.auth_sre_api_keys or "").strip()
            if not keys_raw:
                raise ValueError(
                    "Production configuration error: AUTH_SRE_API_KEYS must not be empty or missing when ENVIRONMENT=production."
                )

            # 4. Reject default demo AUTH_SRE_API_KEYS string
            if keys_raw == DEFAULT_AUTH_SRE_API_KEYS:
                raise ValueError(
                    "Production configuration error: Default demo AUTH_SRE_API_KEYS are forbidden when ENVIRONMENT=production. "
                    "Production SRE API keys must be configured."
                )

            # 5. Reject if any configured key is a known demo key identifier
            for entry in keys_raw.split(","):
                k = entry.split(":")[0].strip()
                if k in DEMO_SRE_API_KEYS:
                    raise ValueError(
                        "Production configuration error: Demo SRE API key identifier is forbidden in AUTH_SRE_API_KEYS when ENVIRONMENT=production."
                    )
        return self

    @model_validator(mode="after")
    def _validate_secrets_hook(self) -> "Settings":
        return self.validate_production_secrets()


# Global settings singleton
settings = Settings()
