"""
Finance Tracker API — Application Entry Point

Starts up the FastAPI application with:
- Structured logging
- Middleware (CORS, security headers, rate limiting, request ID, logging)
- API routes (v1)
- Health check endpoint (includes Redis status)
- Database & Redis connection verification on startup
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

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

    # Redis — non-fatal; fail-open if unavailable
    from app.core.redis import get_redis
    redis = await get_redis()
    if redis is None:
        log.warning(
            "redis_unavailable_on_startup",
            detail="Rate limiting is disabled. Set REDIS_URL in .env to enable."
        )
    else:
        log.info("redis_connected")

    yield  # application runs here

    # ── Shutdown ─────────────────────────────────────────────────────
    from app.core.redis import close_redis
    await close_redis()
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
        description=(
            "**Finance Tracker Family App** — Backend REST API\n\n"
            "Manajemen keuangan keluarga dengan fitur:\n"
            "- 👨‍👩‍👧 Sistem keluarga & undangan\n"
            "- ✅ Task & reward system untuk anak\n"
            "- 💰 Wallet, uang saku, dan fund request\n"
            "- 🎯 Savings goals & milestone tracking\n"
            "- 🔔 Notifikasi real-time\n"
            "- ⭐ PTS reward & exchange\n"
            "- 📊 Subscription tiers (FREE / PRO)"
        ),
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        openapi_tags=[
            {"name": "Auth", "description": "Registrasi, login, refresh token, dan logout."},
            {"name": "Users", "description": "Profil pengguna dan manajemen akun."},
            {"name": "Families", "description": "Buat dan kelola keluarga."},
            {"name": "Invitations", "description": "Undang anggota baru ke keluarga."},
            {"name": "Tasks", "description": "Tugas anak, submission, approval, dan reward."},
            {"name": "Wallets", "description": "Saldo wallet, top-up, dan PTS exchange."},
            {"name": "Transactions", "description": "Ledger transaksi (immutable)."},
            {"name": "Allowances", "description": "Uang saku terjadwal dan manual transfer."},
            {"name": "Fund Requests", "description": "Permintaan dana dari anak ke orang tua."},
            {"name": "Expenses", "description": "Pencatatan pengeluaran keluarga."},
            {"name": "Savings Goals", "description": "Target tabungan anak dengan milestone tracking."},
            {"name": "Notifications", "description": "Notifikasi sistem untuk aktivitas penting."},
            {"name": "Subscriptions", "description": "Manajemen langganan keluarga (FREE/PRO)."},
            {"name": "System", "description": "Health check dan status sistem."},
        ],
        lifespan=lifespan,
    )

    # Register middleware (order matters — see middleware.py)
    register_middleware(application)

    # Register global exception handlers
    register_exception_handlers(application)

    # ── Health check ─────────────────────────────────────────────────
    @application.get("/health", tags=["System"], summary="Health Check",
                     description="Returns API status, database, and Redis connectivity.")
    async def health_check():
        from app.core.redis import check_redis_connection
        db_ok = await check_database_connection()
        redis_ok = await check_redis_connection()
        status = "ok" if db_ok else "degraded"
        return {
            "status": status,
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "database": "connected" if db_ok else "disconnected",
            "redis": "connected" if redis_ok else "unavailable",
            "rate_limiting": "enabled" if redis_ok else "disabled (Redis unavailable)",
        }

    # ── API Routes ────────────────────────────────────────────────────
    application.include_router(api_router, prefix="/api/v1")

    return application


# Module-level app instance — used by uvicorn
app = create_app()
