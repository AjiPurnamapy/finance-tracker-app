"""
Invitation service — invite code generation and family join flow.

Lifecycle:
  Parent creates invitation → code generated, expires in 24h (status=sent)
  Child uses code → joined family (status=accepted)
  Parent cancels → status=cancelled
  Background cleanup → status=expired (for past expires_at)
"""

import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import FamilyMemberRole, InvitationStatus
from app.core.exceptions import (
    AlreadyMemberException,
    BadRequestException,
    ForbiddenException,
    InvitationAlreadyUsedException,
    InvitationCancelledException,
    InvitationExpiredException,
    NotFoundException,
    SeatLimitException,
)
from app.models.family import Family, FamilyMember
from app.models.invitation import Invitation
from app.models.user import User
from app.schemas.family import (
    CreateInvitationRequest,
    FamilyDetailResponse,
    InvitationResponse,
)
from app.services.family_service import (
    _get_active_membership,
    _get_family_members_data,
    get_active_seat_count,
)
from app.utils.invite_code import generate_unique_invite_code

log = structlog.get_logger(__name__)

_INVITATION_EXPIRE_HOURS = 24
_MAX_PENDING_INVITATIONS = 5  # H2: limit invitation spam


async def create_invitation(
    user: User,
    data: CreateInvitationRequest,
    db: AsyncSession,
) -> InvitationResponse:
    """
    Parent creates an invitation code for a child.
    - User must be parent + be in a family as admin
    - Family must not be full
    - Max 5 pending invitations per family
    """
    if user.role != "parent":
        raise ForbiddenException(
            code="PARENT_ROLE_REQUIRED",
            message="Hanya parent yang bisa membuat undangan.",
        )

    # H1: Get user's family membership — verify ADMIN role (defense-in-depth)
    membership = await db.scalar(
        select(FamilyMember).where(
            FamilyMember.user_id == user.id,
            FamilyMember.is_active == True,  # noqa: E712
            FamilyMember.role == FamilyMemberRole.ADMIN,
        )
    )
    if not membership:
        raise NotFoundException(
            resource="Family",
            code="NOT_IN_FAMILY",
        )

    family = await db.get(Family, membership.family_id)
    if not family:
        raise NotFoundException(resource="Family")

    # Check seat limit
    current_seats = await get_active_seat_count(family.id, db)
    if current_seats >= family.max_seats:
        raise SeatLimitException()

    # H2: Check pending invitation limit
    from sqlalchemy import func as sqlfunc

    pending_count = await db.scalar(
        select(sqlfunc.count(Invitation.id)).where(
            Invitation.family_id == family.id,
            Invitation.status == InvitationStatus.SENT,
        )
    )
    if (pending_count or 0) >= _MAX_PENDING_INVITATIONS:
        raise BadRequestException(
            code="TOO_MANY_PENDING_INVITATIONS",
            message=f"Maksimal {_MAX_PENDING_INVITATIONS} undangan pending. "
                    "Batalkan undangan lama terlebih dahulu.",
        )

    # Generate unique invite code
    code = await generate_unique_invite_code(db)
    expires_at = datetime.now(UTC) + timedelta(hours=_INVITATION_EXPIRE_HOURS)

    invitation = Invitation(
        family_id=family.id,
        invited_by=user.id,
        invite_code=code,
        invitee_name=data.invitee_name,
        status=InvitationStatus.SENT,
        expires_at=expires_at,
    )
    db.add(invitation)
    await db.flush()

    log.info(
        "invitation_created",
        family_id=str(family.id),
        code=code,
        created_by=str(user.id),
    )
    return InvitationResponse.model_validate(invitation)


async def join_family(
    user: User,
    invite_code: str,
    db: AsyncSession,
) -> FamilyDetailResponse:
    """
    Child joins a family using a 6-digit invite code.

    Guards:
    - Code must exist and be in status=sent
    - Code must not be expired
    - Family must not be full
    - User must not already be in a family
    """
    # Find invitation by code
    invitation = await db.scalar(
        select(Invitation).where(Invitation.invite_code == invite_code)
    )
    if not invitation:
        raise NotFoundException(resource="Invitation")

    # M4: Check lifecycle status — separate exception for cancelled vs expired
    if invitation.status == InvitationStatus.ACCEPTED:
        raise InvitationAlreadyUsedException()
    if invitation.status == InvitationStatus.CANCELLED:
        raise InvitationCancelledException()
    if invitation.status == InvitationStatus.EXPIRED:
        raise InvitationExpiredException()

    # Compare expiry against timezone-naive current time for SQLite compat
    now_utc = datetime.now(UTC)
    expires_at = invitation.expires_at
    # Normalize to naive UTC for comparison if needed
    if expires_at.tzinfo is not None:
        expires_at_cmp = expires_at.replace(tzinfo=None)
        now_cmp = now_utc.replace(tzinfo=None)
    else:
        expires_at_cmp = expires_at
        now_cmp = now_utc.replace(tzinfo=None)

    if now_cmp > expires_at_cmp:
        invitation.status = InvitationStatus.EXPIRED
        db.add(invitation)
        await db.flush()
        raise InvitationExpiredException()

    # Check user not already in a family
    existing_membership = await _get_active_membership(user.id, db)
    if existing_membership:
        raise AlreadyMemberException()

    # H3: Check seat limit — re-verify after adding member
    family = await db.get(Family, invitation.family_id)
    if not family:
        raise NotFoundException(resource="Family")

    current_seats = await get_active_seat_count(family.id, db)
    if current_seats >= family.max_seats:
        raise SeatLimitException()

    # Add user as member
    new_member = FamilyMember(
        family_id=family.id,
        user_id=user.id,
        role=FamilyMemberRole.MEMBER,
        is_active=True,
    )
    db.add(new_member)

    # Mark invitation as accepted
    invitation.status = InvitationStatus.ACCEPTED
    invitation.accepted_by = user.id
    db.add(invitation)

    await db.flush()

    # H3: Post-insert seat verification (defense against race condition)
    final_seats = await get_active_seat_count(family.id, db)
    if final_seats > family.max_seats:
        # Race condition detected — rollback the join
        raise SeatLimitException()

    log.info(
        "family_joined",
        family_id=str(family.id),
        user_id=str(user.id),
        invite_code=invite_code,
    )

    # Return full family detail
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


async def list_family_invitations(
    user: User,
    db: AsyncSession,
) -> list[InvitationResponse]:
    """Return all invitations for the user's family (parent only)."""
    if user.role != "parent":
        raise ForbiddenException(
            code="PARENT_ROLE_REQUIRED",
            message="Hanya parent yang bisa melihat daftar undangan.",
        )

    membership = await _get_active_membership(user.id, db)
    if not membership:
        raise NotFoundException(resource="Family", code="NOT_IN_FAMILY")

    result = await db.execute(
        select(Invitation)
        .where(Invitation.family_id == membership.family_id)
        .order_by(Invitation.created_at.desc())
    )
    invitations = result.scalars().all()
    return [InvitationResponse.model_validate(inv) for inv in invitations]


async def cancel_invitation(
    invitation_id: uuid.UUID,
    user: User,
    db: AsyncSession,
) -> None:
    """Cancel a pending invitation. Only creator can cancel."""
    invitation = await db.get(Invitation, invitation_id)
    if not invitation:
        raise NotFoundException(resource="Invitation")

    # Only the sender can cancel
    if invitation.invited_by != user.id:
        raise ForbiddenException(
            code="NOT_INVITATION_OWNER",
            message="Anda tidak bisa membatalkan undangan milik orang lain.",
        )

    if invitation.status != InvitationStatus.SENT:
        raise ForbiddenException(
            code="INVITATION_NOT_CANCELLABLE",
            message=f"Undangan dengan status '{invitation.status.value}' tidak bisa dibatalkan.",
        )

    invitation.status = InvitationStatus.CANCELLED
    db.add(invitation)
    await db.flush()

    log.info("invitation_cancelled", invitation_id=str(invitation_id), by=str(user.id))
