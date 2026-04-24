"""
Database Seed Script — Development & Testing Data

Populates the database with realistic sample data for development.
Safe to run multiple times (idempotent — checks before inserting).

Usage:
    cd backend
    python -m app.utils.seed

Data created:
    - 1 parent user  (parent@demo.com / Demo1234)
    - 1 child user   (child@demo.com / Demo1234)
    - 1 family       "Keluarga Demo"
    - PTS exchange rate (1000 PTS = Rp 10.000)
    - 3 sample tasks
    - 1 savings goal for child
"""

import asyncio
import sys
import os

# Ensure app is importable when run as a module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import configure_logging
from app.core.security import hash_password
from app.database import get_session_factory
from app.models.family import Family, FamilyMember
from app.models.pts_exchange_rate import PtsExchangeRate
from app.models.savings_goal import SavingsGoal
from app.models.subscription import Subscription
from app.models.task import Task
from app.models.user import User
from app.models.wallet import Wallet
from app.core.constants import (
    FamilyMemberRole,
    SubscriptionStatus,
    SubscriptionTier,
    TaskStatus,
)

configure_logging()
log = structlog.get_logger(__name__)

PARENT_EMAIL = "parent@demo.com"
CHILD_EMAIL = "child@demo.com"
DEMO_PASSWORD = "Demo1234"
FAMILY_NAME = "Keluarga Demo"


async def seed(db: AsyncSession) -> None:
    log.info("seed_start")

    # ── 1. Parent User ────────────────────────────────────────────────
    parent = await db.scalar(select(User).where(User.email == PARENT_EMAIL))
    if not parent:
        parent = User(
            email=PARENT_EMAIL,
            hashed_password=hash_password(DEMO_PASSWORD),
            full_name="Bapak Demo",
            role="parent",
            is_active=True,
        )
        db.add(parent)
        await db.flush()

        parent_wallet = Wallet(user_id=parent.id)
        db.add(parent_wallet)
        await db.flush()
        log.info("created_parent", email=PARENT_EMAIL)
    else:
        parent_wallet = await db.scalar(select(Wallet).where(Wallet.user_id == parent.id))
        log.info("parent_exists", email=PARENT_EMAIL)

    # ── 2. Child User ─────────────────────────────────────────────────
    child = await db.scalar(select(User).where(User.email == CHILD_EMAIL))
    if not child:
        child = User(
            email=CHILD_EMAIL,
            hashed_password=hash_password(DEMO_PASSWORD),
            full_name="Anak Demo",
            role="child",
            is_active=True,
        )
        db.add(child)
        await db.flush()

        child_wallet = Wallet(user_id=child.id)
        db.add(child_wallet)
        await db.flush()
        log.info("created_child", email=CHILD_EMAIL)
    else:
        child_wallet = await db.scalar(select(Wallet).where(Wallet.user_id == child.id))
        log.info("child_exists", email=CHILD_EMAIL)

    # ── 3. Family ─────────────────────────────────────────────────────
    family = await db.scalar(select(Family).where(Family.name == FAMILY_NAME))
    if not family:
        family = Family(name=FAMILY_NAME, created_by=parent.id)
        db.add(family)
        await db.flush()

        # Parent membership (admin)
        db.add(FamilyMember(
            family_id=family.id,
            user_id=parent.id,
            role=FamilyMemberRole.ADMIN,
            is_active=True,
        ))
        # Child membership (member)
        db.add(FamilyMember(
            family_id=family.id,
            user_id=child.id,
            role=FamilyMemberRole.MEMBER,
            is_active=True,
        ))
        await db.flush()

        # Default free subscription
        db.add(Subscription(
            family_id=family.id,
            tier=SubscriptionTier.FREE,
            status=SubscriptionStatus.ACTIVE,
            max_seats=2,
        ))
        await db.flush()
        log.info("created_family", name=FAMILY_NAME)
    else:
        log.info("family_exists", name=FAMILY_NAME)

    # ── 4. PTS Exchange Rate ─────────────────────────────────────────
    existing_rate = await db.scalar(
        select(PtsExchangeRate).where(PtsExchangeRate.is_active == True)  # noqa: E712
    )
    if not existing_rate:
        db.add(PtsExchangeRate(
            pts_amount=1000,
            idr_amount=10000,
            is_active=True,
        ))
        await db.flush()
        log.info("created_pts_rate", pts=1000, idr=10000)
    else:
        log.info("pts_rate_exists")

    # ── 5. Sample Tasks ───────────────────────────────────────────────
    task_count = await db.scalar(
        select(
            __import__("sqlalchemy", fromlist=["func"]).func.count()
        ).select_from(Task).where(Task.family_id == family.id)
    )
    if task_count == 0:
        sample_tasks = [
            Task(
                family_id=family.id,
                created_by=parent.id,
                assigned_to=child.id,
                title="Cuci Piring",
                description="Cuci semua piring setelah makan malam",
                reward_amount=5000,
                reward_currency="IDR",
                status=TaskStatus.CREATED,
                is_recurring=False,
            ),
            Task(
                family_id=family.id,
                created_by=parent.id,
                assigned_to=child.id,
                title="Rapikan Kamar",
                description="Bersihkan dan rapikan kamar tidur",
                reward_amount=10000,
                reward_currency="IDR",
                status=TaskStatus.CREATED,
                is_recurring=True,
            ),
            Task(
                family_id=family.id,
                created_by=parent.id,
                assigned_to=child.id,
                title="Belajar Matematika 1 Jam",
                description="Kerjakan latihan soal matematika selama 1 jam",
                reward_amount=500,
                reward_currency="PTS",
                status=TaskStatus.CREATED,
                is_recurring=True,
            ),
        ]
        for task in sample_tasks:
            db.add(task)
        await db.flush()
        log.info("created_tasks", count=len(sample_tasks))

    # ── 6. Sample Savings Goal ────────────────────────────────────────
    goal_count = await db.scalar(
        select(
            __import__("sqlalchemy", fromlist=["func"]).func.count()
        ).select_from(SavingsGoal).where(SavingsGoal.user_id == child.id)
    )
    if goal_count == 0:
        db.add(SavingsGoal(
            user_id=child.id,
            name="Nintendo Switch",
            target_amount=3000000,
            current_amount=0,
            is_completed=False,
        ))
        await db.flush()
        log.info("created_savings_goal", name="Nintendo Switch")

    await db.commit()
    log.info("seed_complete")
    print("\n✅ Seed complete! Demo credentials:")
    print(f"   Parent: {PARENT_EMAIL} / {DEMO_PASSWORD}")
    print(f"   Child:  {CHILD_EMAIL} / {DEMO_PASSWORD}")
    print(f"   Family: {FAMILY_NAME}\n")


async def main() -> None:
    session_factory = get_session_factory()
    async with session_factory() as db:
        await seed(db)


if __name__ == "__main__":
    asyncio.run(main())
