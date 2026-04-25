"""
Async database engine and session management.
Uses SQLAlchemy 2.0 async with asyncpg driver.

Engine and session factory are created lazily (not at module import time)
to avoid crashing when PostgreSQL is unavailable (e.g., during testing).
"""

from collections.abc import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

log = structlog.get_logger(__name__)

# ------------------------------------------------------------------ #
# Lazy-initialized singletons
# ------------------------------------------------------------------ #
_engine = None
_async_session_factory = None


def get_engine():
    """
    Lazily create and cache the async engine.
    Called on first actual database use, not on import.
    """
    global _engine
    if _engine is None:
        settings = get_settings()
        url = settings.DATABASE_URL

        if url.startswith("sqlite"):
            # SQLite: tidak support connection pool args
            _engine = create_async_engine(
                url,
                connect_args={"check_same_thread": False},
                echo=settings.is_development,
            )
        else:
            # PostgreSQL: full connection pool config
            _engine = create_async_engine(
                url,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,   # recycle connections every 30 min
                echo=settings.is_development,   # log SQL queries in dev only
            )
    return _engine


def get_session_factory():
    """
    Lazily create and cache the session factory.
    Depends on the engine being initialized first.
    """
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,  # keep objects usable after commit
            autoflush=False,
            autocommit=False,
        )
    return _async_session_factory


# ------------------------------------------------------------------ #
# FastAPI dependency — inject into route handlers
# ------------------------------------------------------------------ #
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async database session dependency for FastAPI.

    Usage in router:
        @router.get("/")
        async def my_route(db: AsyncSession = Depends(get_db)):
            ...

    Automatically commits on success, rolls back on exception.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ------------------------------------------------------------------ #
# Health check helper
# ------------------------------------------------------------------ #
async def check_database_connection() -> bool:
    """
    Verifies the database is reachable.
    Used in the /health endpoint and on startup.
    """
    from sqlalchemy import text

    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        log.error("database_connection_failed", error=str(exc))
        return False


# ------------------------------------------------------------------ #
# Reset (for testing — allows overriding engine/session)
# ------------------------------------------------------------------ #
def reset_engine() -> None:
    """
    Reset the engine and session factory singletons.
    Used in tests to swap in a test database.
    """
    global _engine, _async_session_factory
    _engine = None
    _async_session_factory = None
