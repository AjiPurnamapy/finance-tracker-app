"""
Application configuration — reads from .env file.
All settings are type-safe and validated at startup.
If a required variable is missing, the app will crash immediately (fail-fast).

IMPORTANT: Settings are loaded lazily via get_settings() to avoid
crashing on import during testing or CI/CD environments.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ------------------------------------------------------------------ #
    # Application
    # ------------------------------------------------------------------ #
    APP_NAME: str = "Finance Tracker API"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "DEBUG"

    # ------------------------------------------------------------------ #
    # Database
    # ------------------------------------------------------------------ #
    DATABASE_URL: str

    # ------------------------------------------------------------------ #
    # Security — JWT & Password
    # ------------------------------------------------------------------ #
    SECRET_KEY: str
    SECRET_PEPPER: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ------------------------------------------------------------------ #
    # CORS
    # ------------------------------------------------------------------ #
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # ------------------------------------------------------------------ #
    # Redis
    # ------------------------------------------------------------------ #
    REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_AUTH_RPM: int = 10        # requests/min on /auth endpoints
    RATE_LIMIT_GENERAL_RPM: int = 120    # requests/min on other endpoints

    # ------------------------------------------------------------------ #
    # PTS Exchange
    # ------------------------------------------------------------------ #
    DEFAULT_PTS_TO_IDR_RATE: float = 10.0   # 1000 PTS = Rp 10.000
    MIN_PTS_EXCHANGE: int = 100             # minimum 100 PTS per exchange

    # ------------------------------------------------------------------ #
    # Computed properties
    # ------------------------------------------------------------------ #
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT == "testing"

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        # Allow SQLite for testing, require PostgreSQL for everything else
        if v.startswith("sqlite"):
            return v
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use 'postgresql+asyncpg://' scheme for async support, "
                "or 'sqlite+aiosqlite://' for testing."
            )
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings singleton — loaded lazily on first call.
    NOT executed at module import time to avoid crashing tests/CI.

    Usage:
        from app.config import get_settings
        settings = get_settings()
    """
    return Settings()
