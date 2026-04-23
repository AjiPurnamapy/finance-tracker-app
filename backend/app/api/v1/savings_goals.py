"""
Savings Goals router — endpoints untuk target tabungan anak.
"""

import uuid
from typing import List
from decimal import Decimal

from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.savings_goal import (
    SavingsGoalCreate,
    SavingsGoalUpdate,
    SavingsGoalResponse,
)
from app.services import savings_goal_service

router = APIRouter()


@router.post("", response_model=SavingsGoalResponse, status_code=201)
async def create_goal(
    data: SavingsGoalCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await savings_goal_service.create_goal(current_user, data, db)


@router.get("", response_model=List[SavingsGoalResponse])
async def list_goals(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await savings_goal_service.list_goals(current_user, db)


@router.patch("/{goal_id}", response_model=SavingsGoalResponse)
async def update_goal(
    goal_id: uuid.UUID,
    data: SavingsGoalUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await savings_goal_service.update_goal(goal_id, current_user, data, db)


@router.post("/{goal_id}/contribute", response_model=SavingsGoalResponse)
async def contribute(
    goal_id: uuid.UUID,
    amount: Decimal = Body(..., embed=True),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await savings_goal_service.contribute(goal_id, current_user, amount, db)


@router.delete("/{goal_id}", status_code=204)
async def delete_goal(
    goal_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await savings_goal_service.delete_goal(goal_id, current_user, db)
