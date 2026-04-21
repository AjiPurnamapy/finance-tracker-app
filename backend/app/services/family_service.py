"""
Family service — all family management business logic.

Rules enforced here:
- Only parent can create a family
- A user can only be in ONE family at a time
- Only the family admin (creator) can remove members
- Admin cannot be removed
- Seat limit enforced by SUBSCRIPTION_MAX_SEATS constant
"""

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    SUBSCRIPTION_MAX_SEATS,
    FamilyMemberRole,
    SubscriptionTier,
)
from app.core.exceptions import (
    AlreadyMemberException,
    FamilyAlreadyExistsException,
    ForbiddenException,
    NotFoundException,
)
from app.models.family import Family, FamilyMember
from app.models.user import User
from app.schemas.family import (
    CreateFamilyRequest,
    FamilyDetailResponse,
    FamilyMemberResponse,
    FamilyResponse,
)

log = structlog.get_logger(__name__)


async def _get_active_membership(
    user_id: uuid.UUID, db: AsyncSession
) -> FamilyMember | None:
    """Return the user's active FamilyMember record, or None."""
    return await db.scalar(
        select(FamilyMember).where(
            FamilyMember.user_id == user_id,
            FamilyMember.is_active == True,  # noqa: E712
        )
    )


async def _get_family_or_404(family_id: uuid.UUID, db: AsyncSession) -> Family:
    family = await db.get(Family, family_id)
    if not family:
        raise NotFoundException(resource="Family")
    return family


def _build_member_response(member: FamilyMember, user: User) -> FamilyMemberResponse:
    return FamilyMemberResponse(
        id=member.id,
        family_id=member.family_id,
        user_id=member.user_id,
        full_name=user.full_name,
        email=user.email,
        role=member.role,
        is_active=member.is_active,
        joined_at=member.joined_at,
    )


# ------------------------------------------------------------------ #
# Public API
# ------------------------------------------------------------------ #

async def create_family(
    user: User,
    data: CreateFamilyRequest,
    db: AsyncSession,
) -> FamilyResponse:
    """
    Create a new family.
    - User must be parent
    - User must not already be in a family
    - User must not already own a family
    """
    if user.role != "parent":
        raise ForbiddenException(
            code="PARENT_ROLE_REQUIRED",
            message="Hanya parent yang bisa membuat family.",
        )

    # Check user doesn't already own a family
    existing_family = await db.scalar(
        select(Family).where(Family.created_by == user.id)
    )
    if existing_family:
        raise FamilyAlreadyExistsException()

    # Check user not already a member somewhere
    existing_membership = await _get_active_membership(user.id, db)
    if existing_membership:
        raise AlreadyMemberException()

    # Create family
    family = Family(
        name=data.name.strip(),
        created_by=user.id,
        max_seats=SUBSCRIPTION_MAX_SEATS[SubscriptionTier.FREE],
    )
    db.add(family)
    await db.flush()

    # Auto-add creator as admin member
    admin_member = FamilyMember(
        family_id=family.id,
        user_id=user.id,
        role=FamilyMemberRole.ADMIN,
        is_active=True,
    )
    db.add(admin_member)
    await db.flush()

    log.info("family_created", family_id=str(family.id), user_id=str(user.id))
    return FamilyResponse.model_validate(family)


async def get_user_family(
    user: User,
    db: AsyncSession,
) -> FamilyDetailResponse:
    """Get the family the user currently belongs to, with member list."""
    membership = await _get_active_membership(user.id, db)
    if not membership:
        raise NotFoundException(
            resource="Family",
            code="NOT_IN_FAMILY",
        )

    family = await _get_family_or_404(membership.family_id, db)
    members = await _get_family_members_data(family.id, db)

    return FamilyDetailResponse(
        id=family.id,
        name=family.name,
        created_by=family.created_by,
        max_seats=family.max_seats,
        member_count=len(members),
        members=members,
        created_at=family.created_at,
    )


async def _get_family_members_data(
    family_id: uuid.UUID, db: AsyncSession
) -> list[FamilyMemberResponse]:
    """Load all active members of a family with their user data via JOIN."""
    result = await db.execute(
        select(FamilyMember, User)
        .join(User, FamilyMember.user_id == User.id)
        .where(
            FamilyMember.family_id == family_id,
            FamilyMember.is_active == True,  # noqa: E712
        )
        .order_by(FamilyMember.joined_at)
    )
    rows = result.all()
    return [_build_member_response(member, user) for member, user in rows]


async def get_members(
    family_id: uuid.UUID,
    user: User,
    db: AsyncSession,
) -> list[FamilyMemberResponse]:
    """
    Return active member list for a family.
    Requester must be an active member of that family.
    """
    membership = await _get_active_membership(user.id, db)
    if not membership or membership.family_id != family_id:
        raise ForbiddenException(
            code="NOT_FAMILY_MEMBER",
            message="Anda bukan anggota family ini.",
        )
    return await _get_family_members_data(family_id, db)


async def remove_member(
    family_id: uuid.UUID,
    target_user_id: uuid.UUID,
    requester: User,
    db: AsyncSession,
) -> None:
    """
    Remove (deactivate) a member from the family.
    - Requester must be family admin
    - Cannot remove self (admin)
    - Cannot remove another admin
    """
    # Verify requester IS an admin of this family
    requester_membership = await db.scalar(
        select(FamilyMember).where(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == requester.id,
            FamilyMember.is_active == True,  # noqa: E712
            FamilyMember.role == FamilyMemberRole.ADMIN,
        )
    )
    if not requester_membership:
        raise ForbiddenException(
            code="ADMIN_ROLE_REQUIRED",
            message="Hanya admin family yang bisa menghapus anggota.",
        )

    # Cannot remove self
    if target_user_id == requester.id:
        raise ForbiddenException(
            code="CANNOT_REMOVE_SELF",
            message="Anda tidak bisa menghapus diri sendiri dari family.",
        )

    # Find target membership
    target_membership = await db.scalar(
        select(FamilyMember).where(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == target_user_id,
            FamilyMember.is_active == True,  # noqa: E712
        )
    )
    if not target_membership:
        raise NotFoundException(resource="Family member")

    # Cannot remove another admin
    if target_membership.role == FamilyMemberRole.ADMIN:
        raise ForbiddenException(
            code="CANNOT_REMOVE_ADMIN",
            message="Admin family tidak bisa dihapus.",
        )

    target_membership.is_active = False
    db.add(target_membership)
    await db.flush()

    log.info(
        "member_removed",
        family_id=str(family_id),
        removed_user=str(target_user_id),
        by_admin=str(requester.id),
    )


async def get_active_seat_count(family_id: uuid.UUID, db: AsyncSession) -> int:
    """Return number of currently active seats in a family."""
    from sqlalchemy import func as sqlfunc

    result = await db.scalar(
        select(sqlfunc.count(FamilyMember.id)).where(
            FamilyMember.family_id == family_id,
            FamilyMember.is_active == True,  # noqa: E712
        )
    )
    return result or 0
