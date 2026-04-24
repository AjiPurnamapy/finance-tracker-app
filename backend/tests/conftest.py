"""
pytest configuration and shared fixtures.
Uses in-memory SQLite for fast, isolated tests (no real PostgreSQL needed).

Environment variables are overridden BEFORE any app imports to ensure
config validation passes with SQLite test database URL.
"""

import os

# ── Override env BEFORE importing any app code ────────────────────────
# This prevents config.py from requiring a real PostgreSQL URL
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("SECRET_PEPPER", "test-pepper-not-for-production")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("LOG_LEVEL", "WARNING")
# Disable rate limiting in tests (Redis is not available in test environment)
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings  # noqa: E402
from app.database import get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.base import Base  # noqa: E402
import app.models  # noqa: E402, F401 — ensure ALL models are registered with Base

# ------------------------------------------------------------------ #
# Clear cached settings so test env vars take effect
# ------------------------------------------------------------------ #
get_settings.cache_clear()

# ------------------------------------------------------------------ #
# Test database (SQLite in-memory)
# ------------------------------------------------------------------ #

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create a fresh in-memory SQLite engine for each test function."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncSession:
    """Provide a database session that rolls back after each test."""
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session) -> AsyncClient:
    """
    Async test client with overridden database dependency.
    All requests use the test database session automatically.
    """
    test_app = create_app()

    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as ac:
        yield ac

    test_app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def pts_exchange_rate(db_session: AsyncSession):
    """
    Seed an active PTS exchange rate into the test DB.
    Required by any test involving PTS exchange (1000 PTS = Rp 10.000).
    """
    from app.models.pts_exchange_rate import PtsExchangeRate

    rate = PtsExchangeRate(
        pts_amount=1000,
        idr_amount=10000,
        is_active=True,
    )
    db_session.add(rate)
    await db_session.flush()
    return rate
