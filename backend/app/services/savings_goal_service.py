import uuid
from decimal import Decimal
from typing import List

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import Currency, NotificationType
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
from app.services import wallet_service
from app.services.notification_service import create_notification

log = structlog.get_logger(__name__)

async def create_goal(
    user: User, data: SavingsGoalCreate, db: AsyncSession
) -> SavingsGoalResponse:
    if user.role != "child":
        raise ForbiddenException(code="CHILD_ROLE_REQUIRED", message="Hanya child yang bisa membuat savings goal.")

    goal = SavingsGoal(
        user_id=user.id,
        name=data.name,
        target_amount=data.target_amount,
        current_amount=Decimal("0.00"),
        is_completed=False,
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
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

    await db.commit()
    await db.refresh(goal)
    return SavingsGoalResponse.model_validate(goal)

async def contribute(
    goal_id: uuid.UUID, user: User, amount: Decimal, db: AsyncSession
) -> SavingsGoalResponse:
    goal = await _get_goal_or_404(goal_id, user.id, db)

    if goal.is_completed:
        raise BadRequestException(code="GOAL_COMPLETED", message="Goal ini sudah tercapai.")
        
    if amount <= 0:
         raise BadRequestException(code="INVALID_AMOUNT", message="Amount harus lebih besar dari 0.")

    # Get user's wallet
    wallet = await wallet_service.get_wallet(user, db)

    # Debit wallet (this handles optimistic locking and insufficient balance)
    await wallet_service.debit(wallet_id=wallet.id, amount=amount, currency=Currency.IDR, db=db)

    # Update goal
    old_percentage = (goal.current_amount / goal.target_amount) * 100
    goal.current_amount += amount
    new_percentage = (goal.current_amount / goal.target_amount) * 100

    if goal.current_amount >= goal.target_amount:
        goal.current_amount = goal.target_amount
        goal.is_completed = True
        
    await db.commit()
    await db.refresh(goal)

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

    return SavingsGoalResponse.model_validate(goal)

async def delete_goal(goal_id: uuid.UUID, user: User, db: AsyncSession) -> None:
    goal = await _get_goal_or_404(goal_id, user.id, db)

    # Refund if not empty
    if goal.current_amount > 0:
        wallet = await wallet_service.get_wallet(user, db)
        await wallet_service.credit(wallet_id=wallet.id, amount=goal.current_amount, currency=Currency.IDR, db=db)

    await db.delete(goal)
    await db.commit()

async def _get_goal_or_404(goal_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> SavingsGoal:
    try:
        goal_uuid = uuid.UUID(str(goal_id))
    except ValueError:
        raise NotFoundException(resource="Savings Goal")

    query = select(SavingsGoal).where(
        SavingsGoal.id == goal_uuid,
        SavingsGoal.user_id == user_id
    )
    result = await db.execute(query)
    goal = result.scalar_one_or_none()

    if not goal:
        raise NotFoundException(resource="Savings Goal")
    return goal
