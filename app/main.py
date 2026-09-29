"""IncidentOps Copilot - SRE Continuous Memory Agent FastAPI Application."""

from contextlib import asynccontextmanager
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.config import settings
from app.core.observability import CorrelationIdMiddleware, StructuredJsonFormatter

# Configure structured logging
root_logger = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(StructuredJsonFormatter())
root_logger.handlers = [handler]
root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

logger = logging.getLogger("incidentops.main")

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events: startup checks and resource teardown."""
    # Enforce fail-closed production secret validation at application startup (Phase 7.4A)
    settings.validate_production_secrets()

    logger.info("=======================================================")
    logger.info(" IncidentOps Copilot — SRE Continuous Memory Agent")
    logger.info("=======================================================")
    logger.info("Runtime Environment: %s", settings.environment)
    logger.info("Hindsight Endpoint:  %s", settings.hindsight_api_url)
    logger.info("Hindsight Bank ID:   %s", settings.hindsight_bank_id)
    logger.info("Hindsight Auth:      %s", "Configured (API Key Present)" if settings.is_hindsight_configured else "Unauthenticated")
    logger.info("Groq Model:          %s", settings.groq_model)
    logger.info("Groq API Key:        %s", "Configured" if settings.is_groq_configured else "Missing (fallback engine enabled)")
    logger.info("Auth Secrets:        %s", "Production Verified (Strict)" if settings.environment.lower() == "production" else "Development / Demo Credentials Active")
    logger.info("=======================================================")
    yield
    logger.info("Shutting down IncidentOps Copilot...")


app = FastAPI(
    title="IncidentOps Copilot — SRE Continuous Memory Agent",
    description=(
        "Mission-critical SRE incident triage agent pairing Hindsight Cloud persistent memory "
        "as the central intelligence engine with Groq inference (Llama 3.3 / Qwen 2.5) and a Python FastAPI backend."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Correlation ID and Request Metrics Middleware
app.add_middleware(CorrelationIdMiddleware)

# Cross-Origin Resource Sharing (Phase 7.8)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True if settings.cors_origins_list != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router)

# Mount Static Assets & Dashboard UI
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def serve_dashboard():
    """Serve the modern SRE Operations Console Dashboard."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "service": "IncidentOps Copilot",
        "documentation": "/docs",
        "api_health": "/api/v1/health",
        "triage": "/api/v1/triage",
    }
