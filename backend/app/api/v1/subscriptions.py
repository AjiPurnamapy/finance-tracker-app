"""
Subscriptions router — endpoints untuk manajemen langganan keluarga.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.subscription import SubscriptionResponse
from app.services import subscription_service

router = APIRouter()


@router.get("", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await subscription_service.get_subscription(current_user, db)


@router.post("/upgrade", response_model=SubscriptionResponse)
async def upgrade_to_pro(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await subscription_service.upgrade_to_pro(current_user, db)


@router.post("/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await subscription_service.cancel_subscription(current_user, db)
