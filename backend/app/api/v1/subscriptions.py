from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.subscription import SubscriptionResponse
from app.services import subscription_service
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await subscription_service.get_subscription(current_user, db)

@router.post("/upgrade", response_model=SubscriptionResponse)
async def upgrade_to_pro(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await subscription_service.upgrade_to_pro(current_user, db)

@router.post("/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await subscription_service.cancel_subscription(current_user, db)
