"""
Alembic environment configuration for async SQLAlchemy.
Reads DATABASE_URL from app settings (not alembic.ini).
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Load app config and all models so Alembic can detect them
from app.config import get_settings
from app.models.base import Base  # noqa: F401 — must import Base

# Import ALL models so their metadata is registered with Base.
# IMPORTANT: Every model file must be imported here — if a model is missing,
# Alembic autogenerate will generate DROP TABLE migrations for those tables.
from app.models.user import User  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.family import Family, FamilyMember  # noqa: F401
from app.models.invitation import Invitation  # noqa: F401
from app.models.wallet import Wallet  # noqa: F401
from app.models.task import Task  # noqa: F401
from app.models.transaction import Transaction  # noqa: F401
# Phase 5+
from app.models.allowance import Allowance  # noqa: F401
from app.models.expense import Expense  # noqa: F401
from app.models.fund_request import FundRequest  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.pts_exchange_rate import PtsExchangeRate  # noqa: F401
from app.models.savings_goal import SavingsGoal  # noqa: F401
from app.models.subscription import Subscription  # noqa: F401

# ------------------------------------------------------------------ #
# Alembic config
# ------------------------------------------------------------------ #
config = context.config

# Override sqlalchemy.url with app settings
config.set_main_option("sqlalchemy.url", get_settings().DATABASE_URL)

# Configure Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for --autogenerate
target_metadata = Base.metadata


# ------------------------------------------------------------------ #
# Run migrations offline (no DB connection)
# ------------------------------------------------------------------ #
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ------------------------------------------------------------------ #
# Run migrations online (with async DB connection)
# ------------------------------------------------------------------ #
def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ------------------------------------------------------------------ #
# Entry point
# ------------------------------------------------------------------ #
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
