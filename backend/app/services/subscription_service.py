import uuid
from typing import Optional
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SubscriptionTier, SubscriptionStatus
from app.core.exceptions import NotFoundException, ForbiddenException
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.subscription import SubscriptionResponse
from app.services.common import get_active_family_membership

log = structlog.get_logger(__name__)

async def get_subscription(user: User, db: AsyncSession) -> SubscriptionResponse:
    # Any active member can view the subscription
    membership = await get_active_family_membership(user, db)
    
    sub = await _get_or_create_default_subscription(membership.family_id, db)
    return SubscriptionResponse.model_validate(sub)

async def upgrade_to_pro(user: User, db: AsyncSession) -> SubscriptionResponse:
    # Only parent/admin can upgrade
    if user.role != "parent":
        raise ForbiddenException(code="PARENT_ROLE_REQUIRED", message="Hanya parent yang bisa mengubah langganan.")
        
    membership = await get_active_family_membership(user, db)
    
    sub = await _get_or_create_default_subscription(membership.family_id, db)
    
    # Logic for upgrade
    sub.tier = SubscriptionTier.PRO
    sub.status = SubscriptionStatus.ACTIVE
    sub.max_seats = 6
    # 1 month expiration from now (mock billing cycle)
    sub.expires_at = datetime.now(timezone.utc) + relativedelta(months=1)
    
    await db.commit()
    await db.refresh(sub)
    
    log.info("subscription_upgraded", family_id=str(membership.family_id), user_id=str(user.id))
    return SubscriptionResponse.model_validate(sub)

async def cancel_subscription(user: User, db: AsyncSession) -> SubscriptionResponse:
    if user.role != "parent":
        raise ForbiddenException(code="PARENT_ROLE_REQUIRED", message="Hanya parent yang bisa mengubah langganan.")
        
    membership = await get_active_family_membership(user, db)
    
    sub = await _get_or_create_default_subscription(membership.family_id, db)
    
    if sub.tier == SubscriptionTier.FREE:
        raise ForbiddenException(code="ALREADY_FREE", message="Family ini masih menggunakan plan gratis.")
        
    sub.status = SubscriptionStatus.CANCELED
    # Expiration remains the same until the billing cycle ends.
    
    await db.commit()
    await db.refresh(sub)
    
    log.info("subscription_canceled", family_id=str(membership.family_id), user_id=str(user.id))
    return SubscriptionResponse.model_validate(sub)

async def _get_or_create_default_subscription(family_id: uuid.UUID, db: AsyncSession) -> Subscription:
    query = select(Subscription).where(Subscription.family_id == family_id)
    result = await db.execute(query)
    sub = result.scalar_one_or_none()
    
    if not sub:
        # Create default free subscription
        sub = Subscription(
            family_id=family_id,
            tier=SubscriptionTier.FREE,
            status=SubscriptionStatus.ACTIVE,
            max_seats=2,
            expires_at=None
        )
        db.add(sub)
        await db.commit()
        await db.refresh(sub)
        
    return sub
