"""
Finance Tracker API — Application Entry Point

Starts up the FastAPI application with:
- Structured logging
- Middleware (CORS, request ID, logging, error handling)
- API routes (v1)
- Health check endpoint
- Database connection verification on startup
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.api.v1.router import api_router
from app.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import register_exception_handlers, register_middleware
from app.database import check_database_connection

log = structlog.get_logger(__name__)


# ------------------------------------------------------------------ #
# Lifespan (startup / shutdown)
# ------------------------------------------------------------------ #

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # ── Startup ──────────────────────────────────────────────────────
    configure_logging()

    log.info(
        "application_starting",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )

    db_ok = await check_database_connection()
    if not db_ok:
        log.error("database_connection_failed_on_startup")
        raise RuntimeError("Cannot connect to database. Check DATABASE_URL in .env")

    log.info("database_connected")

    yield  # application runs here

    # ── Shutdown ─────────────────────────────────────────────────────
    log.info("application_shutting_down")


# ------------------------------------------------------------------ #
# FastAPI app factory
# ------------------------------------------------------------------ #

def create_app() -> FastAPI:
    """
    Application factory — creates and configures the FastAPI instance.
    Using a factory allows tests to create fresh app instances.
    """
    settings = get_settings()

    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Backend API for Finance Tracker Family App",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Register middleware (order matters — see middleware.py)
    register_middleware(application)

    # Register global exception handlers
    register_exception_handlers(application)

    # ── Health check ─────────────────────────────────────────────────
    @application.get("/health", tags=["System"], summary="Health Check")
    async def health_check():
        """
        Returns API status and database connectivity.
        Used by load balancers and deployment pipelines.
        """
        db_ok = await check_database_connection()
        return {
            "status": "ok" if db_ok else "degraded",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "database": "connected" if db_ok else "disconnected",
        }

    # ── API Routes ────────────────────────────────────────────────────
    application.include_router(api_router, prefix="/api/v1")

    return application


# Module-level app instance — used by uvicorn
app = create_app()
