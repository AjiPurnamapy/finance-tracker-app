"""
Common shared helpers for services.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.family import FamilyMember
from app.models.user import User


async def get_active_family_membership(user: User, db: AsyncSession) -> FamilyMember:
    """
    Get active family membership for a user or raise NotFoundException.
    Used across multiple services to verify user is in a family.
    """
    membership = await db.scalar(
        select(FamilyMember).where(
            FamilyMember.user_id == user.id,
            FamilyMember.is_active == True,  # noqa: E712
        )
    )
    if not membership:
        raise NotFoundException(resource="Family", code="NOT_IN_FAMILY")
    return membership
