"""
Savings Goal service — create, update, contribute, delete goals.

Contributions use atomic SQL UPDATE to prevent race conditions
on concurrent requests (same pattern as wallet_service).
"""

import uuid
from decimal import Decimal
from typing import List

import structlog
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import Currency, NotificationType, TransactionType
from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.models.savings_goal import SavingsGoal
from app.models.user import User
from app.schemas.savings_goal import (
    SavingsGoalCreate,
    SavingsGoalUpdate,
    SavingsGoalResponse,
)
from app.services import wallet_service, transaction_service
from app.services.common import get_active_family_membership
from app.services.notification_service import create_notification

log = structlog.get_logger(__name__)

# Maximum number of savings goals per user
MAX_GOALS_PER_USER = 20


async def create_goal(
    user: User, data: SavingsGoalCreate, db: AsyncSession
) -> SavingsGoalResponse:
    if user.role != "child":
        raise ForbiddenException(code="CHILD_ROLE_REQUIRED", message="Hanya child yang bisa membuat savings goal.")

    # M-1: Enforce goal count limit
    count = await db.scalar(
        select(func.count()).select_from(SavingsGoal).where(SavingsGoal.user_id == user.id)
    )
    if count and count >= MAX_GOALS_PER_USER:
        raise BadRequestException(
            code="TOO_MANY_GOALS",
            message=f"Maksimal {MAX_GOALS_PER_USER} savings goals per user.",
        )

    goal = SavingsGoal(
        user_id=user.id,
        name=data.name,
        target_amount=data.target_amount,
        current_amount=Decimal("0.00"),
        is_completed=False,
    )
    db.add(goal)
    await db.flush()
    await db.refresh(goal)

    log.info("savings_goal_created", goal_id=str(goal.id), user_id=str(user.id))
    return SavingsGoalResponse.model_validate(goal)


async def list_goals(user: User, db: AsyncSession) -> List[SavingsGoalResponse]:
    query = select(SavingsGoal).where(SavingsGoal.user_id == user.id)
    result = await db.execute(query)
    goals = result.scalars().all()
    return [SavingsGoalResponse.model_validate(g) for g in goals]


async def update_goal(
    goal_id: uuid.UUID, user: User, data: SavingsGoalUpdate, db: AsyncSession
) -> SavingsGoalResponse:
    goal = await _get_goal_or_404(goal_id, user.id, db)

    if data.name is not None:
        goal.name = data.name
    if data.target_amount is not None:
        if data.target_amount < goal.current_amount:
            raise BadRequestException(
                code="INVALID_TARGET",
                message="Target baru tidak boleh lebih kecil dari jumlah saat ini."
            )
        goal.target_amount = data.target_amount
        if goal.current_amount >= goal.target_amount:
             goal.is_completed = True

    await db.flush()
    await db.refresh(goal)

    log.info("savings_goal_updated", goal_id=str(goal_id), user_id=str(user.id))
    return SavingsGoalResponse.model_validate(goal)


async def contribute(
    goal_id: uuid.UUID, user: User, amount: Decimal, db: AsyncSession
) -> SavingsGoalResponse:
    goal = await _get_goal_or_404(goal_id, user.id, db)

    if goal.is_completed:
        raise BadRequestException(code="GOAL_COMPLETED", message="Goal ini sudah tercapai.")

    if amount <= 0:
         raise BadRequestException(code="INVALID_AMOUNT", message="Amount harus lebih besar dari 0.")

    # M-2: Cap single contribution
    if amount > Decimal("10000000"):
        raise BadRequestException(code="AMOUNT_TOO_LARGE", message="Maksimal kontribusi per transaksi adalah Rp 10.000.000.")

    # Get user's wallet
    wallet = await wallet_service.get_wallet(user, db)

    # Debit wallet (this handles optimistic locking and insufficient balance)
    await wallet_service.debit(wallet_id=wallet.id, amount=amount, currency=Currency.IDR, db=db)

    # Calculate milestone percentages BEFORE update
    old_percentage = (goal.current_amount / goal.target_amount) * 100

    # H-2: Atomic UPDATE to prevent race conditions on concurrent contributions
    new_current = goal.current_amount + amount
    is_now_completed = new_current >= goal.target_amount
    if is_now_completed:
        new_current = goal.target_amount

    await db.execute(
        update(SavingsGoal)
        .where(SavingsGoal.id == goal.id)
        .values(
            current_amount=new_current,
            is_completed=is_now_completed,
        )
    )

    await db.flush()
    await db.refresh(goal)

    # Calculate new percentage for milestone check
    new_percentage = (goal.current_amount / goal.target_amount) * 100

    # Check milestones and notify
    milestones = [25, 50, 75, 100]
    for milestone in milestones:
        if old_percentage < milestone and new_percentage >= milestone:
            await create_notification(
                session=db,
                user_id=user.id,
                type=NotificationType.GOAL_MILESTONE,
                title="Pencapaian Tabungan!",
                message=f"Tabungan '{goal.name}' sudah mencapai {milestone}%!" if milestone < 100 else f"Hore! Tabungan '{goal.name}' sudah terpenuhi 100%!",
                data={"goal_id": str(goal.id), "milestone": milestone}
            )

    log.info(
        "savings_goal_contribution",
        goal_id=str(goal_id),
        user_id=str(user.id),
        amount=str(amount),
        new_current=str(goal.current_amount),
        completed=goal.is_completed,
    )
    return SavingsGoalResponse.model_validate(goal)


async def delete_goal(goal_id: uuid.UUID, user: User, db: AsyncSession) -> None:
    goal = await _get_goal_or_404(goal_id, user.id, db)

    # L-2: Refund if not empty — with transaction record for audit trail
    if goal.current_amount > 0:
        wallet = await wallet_service.get_wallet(user, db)
        await wallet_service.credit(wallet_id=wallet.id, amount=goal.current_amount, currency=Currency.IDR, db=db)

        # Record refund transaction for financial audit trail
        membership = await get_active_family_membership(user, db)
        await transaction_service.create_transaction(
            family_id=membership.family_id,
            source_wallet_id=None,
            destination_wallet_id=wallet.id,
            amount=goal.current_amount,
            currency=Currency.IDR,
            type=TransactionType.BONUS,  # Reuse BONUS type for refund (no new enum needed at MVP)
            description=f"Refund tabungan: {goal.name}",
            reference_type="savings_goal",
            reference_id=goal.id,
            db=db,
        )

    await db.delete(goal)
    await db.flush()

    log.info("savings_goal_deleted", goal_id=str(goal_id), user_id=str(user.id))


async def _get_goal_or_404(goal_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> SavingsGoal:
    query = select(SavingsGoal).where(
        SavingsGoal.id == goal_id,
        SavingsGoal.user_id == user_id
    )
    result = await db.execute(query)
    goal = result.scalar_one_or_none()

    if not goal:
        raise NotFoundException(resource="Savings Goal")
    return goal
