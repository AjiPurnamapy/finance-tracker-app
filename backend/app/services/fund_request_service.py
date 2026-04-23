"""
FundRequest service — sistem permintaan dana dari child ke parent.

State machine:
  pending → approved  (parent approve → transfer executed)
  pending → rejected  (parent reject → no transfer)

Business rules:
- Hanya pending request yang bisa di-review
- Double approve/reject → 400 INVALID_STATE_TRANSITION
- Parent wallet divalidasi sebelum approve
"""

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import FundRequestStatus, TransactionType, NotificationType
from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.models.family import FamilyMember
from app.models.fund_request import FundRequest
from app.models.user import User
from app.schemas.fund_request import (
    CreateFundRequestRequest,
    FundRequestResponse,
)
from app.services.common import get_active_family_membership

log = structlog.get_logger(__name__)


async def create_request(
    child: User,
    data: CreateFundRequestRequest,
    db: AsyncSession,
) -> FundRequestResponse:
    """Child creates a fund request. Must be in a family."""
    if child.role != "child":
        raise ForbiddenException(
            code="CHILD_ROLE_REQUIRED",
            message="Hanya child yang bisa membuat fund request.",
        )

    membership = await get_active_family_membership(child, db)

    # Check pending request limit (max 10)
    pending_count = await db.scalar(
        select(func.count()).where(
            FundRequest.child_id == child.id,
            FundRequest.status == FundRequestStatus.PENDING,
        )
    )
    if pending_count and pending_count >= 10:
        raise BadRequestException(
            code="TOO_MANY_PENDING",
            message="Anda memiliki 10 request yang masih pending. Tunggu parent memprosesnya.",
        )

    fund_request = FundRequest(
        family_id=membership.family_id,
        child_id=child.id,
        amount=data.amount,
        currency=data.currency,
        type=data.type,
        reason=data.reason,
        status=FundRequestStatus.PENDING,
    )
    db.add(fund_request)
    await db.flush()
    await db.refresh(fund_request)

    from app.services.notification_service import create_notification
    # Notify family admins (parents)
    admins = await db.scalars(
        select(FamilyMember.user_id).where(
            FamilyMember.family_id == membership.family_id,
            FamilyMember.role == "admin"
        )
    )
    for admin_id in admins:
        await create_notification(
            session=db,
            user_id=admin_id,
            type=NotificationType.FUND_REQUEST_CREATED,
            title="Permintaan Dana Baru",
            message=f"Anak meminta dana sebesar {fund_request.amount} {fund_request.currency}.",
            data={"request_id": str(fund_request.id)}
        )

    log.info(
        "fund_request_created",
        request_id=str(fund_request.id),
        child_id=str(child.id),
        amount=str(data.amount),
    )
    return FundRequestResponse.model_validate(fund_request)


async def list_requests(
    user: User,
    db: AsyncSession,
    status: FundRequestStatus | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[FundRequestResponse], int]:
    """
    Parent: all requests in family.
    Child: only own requests.
    """
    membership = await get_active_family_membership(user, db)
    family_id = membership.family_id

    if user.role == "parent":
        base_query = select(FundRequest).where(FundRequest.family_id == family_id)
    else:
        base_query = select(FundRequest).where(FundRequest.child_id == user.id)

    if status:
        base_query = base_query.where(FundRequest.status == status)

    total = await db.scalar(
        select(func.count()).select_from(base_query.subquery())
    ) or 0

    offset = (page - 1) * per_page
    result = await db.execute(
        base_query.order_by(FundRequest.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    requests = result.scalars().all()
    return [FundRequestResponse.model_validate(r) for r in requests], total


async def get_request(
    request_id: uuid.UUID,
    user: User,
    db: AsyncSession,
) -> FundRequestResponse:
    """Get fund request. User must be in same family."""
    fund_request = await db.get(FundRequest, request_id)
    if not fund_request:
        raise NotFoundException(resource="FundRequest")

    # Verify user is in the same family
    membership = await db.scalar(
        select(FamilyMember).where(
            FamilyMember.user_id == user.id,
            FamilyMember.family_id == fund_request.family_id,
            FamilyMember.is_active == True,  # noqa: E712
        )
    )
    if not membership:
        raise ForbiddenException(
            code="NOT_FAMILY_MEMBER",
            message="Anda tidak memiliki akses ke fund request ini.",
        )
    return FundRequestResponse.model_validate(fund_request)


async def approve_request(
    request_id: uuid.UUID,
    parent: User,
    db: AsyncSession,
) -> FundRequestResponse:
    """
    Parent approves fund request.
    Debit parent wallet → credit child wallet → create transaction.

    IMPORTANT: All operations within single DB transaction from get_db().
    """
    from app.services import transaction_service, wallet_service

    if parent.role != "parent":
        raise ForbiddenException(
            code="PARENT_ROLE_REQUIRED",
            message="Hanya parent yang bisa menyetujui fund request.",
        )

    fund_request = await db.get(FundRequest, request_id)
    if not fund_request:
        raise NotFoundException(resource="FundRequest")

    # Verify parent is in the same family
    membership = await db.scalar(
        select(FamilyMember).where(
            FamilyMember.user_id == parent.id,
            FamilyMember.family_id == fund_request.family_id,
            FamilyMember.is_active == True,  # noqa: E712
        )
    )
    if not membership:
        raise ForbiddenException(
            code="NOT_FAMILY_MEMBER",
            message="Anda tidak memiliki akses ke fund request ini.",
        )

    # Only pending can be approved
    if fund_request.status != FundRequestStatus.PENDING:
        raise BadRequestException(
            code="INVALID_STATE_TRANSITION",
            message=f"Tidak bisa approve fund request dengan status '{fund_request.status}'.",
        )

    # Get wallets
    parent_wallet = await wallet_service.get_wallet_by_user_id(parent.id, db)
    child_wallet = await wallet_service.get_wallet_by_user_id(fund_request.child_id, db)

    # Debit parent (raises InsufficientBalanceException if not enough)
    await wallet_service.debit(
        wallet_id=parent_wallet.id,
        amount=fund_request.amount,
        currency=fund_request.currency,
        db=db,
    )

    # Credit child
    await wallet_service.credit(
        wallet_id=child_wallet.id,
        amount=fund_request.amount,
        currency=fund_request.currency,
        db=db,
    )

    # Record transaction
    tx = await transaction_service.create_transaction(
        family_id=fund_request.family_id,
        source_wallet_id=parent_wallet.id,
        destination_wallet_id=child_wallet.id,
        amount=fund_request.amount,
        currency=fund_request.currency,
        type=TransactionType.FUND_REQUEST,
        description=f"Fund request approved: {fund_request.reason or 'Transfer dana'}",
        reference_type="fund_request",
        reference_id=fund_request.id,
        db=db,
    )

    # Update request state
    fund_request.status = FundRequestStatus.APPROVED
    fund_request.parent_id = parent.id
    fund_request.reviewed_at = datetime.now(UTC)
    fund_request.transaction_id = tx.id
    db.add(fund_request)
    await db.flush()
    await db.refresh(fund_request)

    from app.services.notification_service import create_notification
    # Notify child
    await create_notification(
        session=db,
        user_id=fund_request.child_id,
        type=NotificationType.FUND_REQUEST_APPROVED,
        title="Permintaan Dana Disetujui!",
        message=f"Permintaan dana sebesar {fund_request.amount} {fund_request.currency} telah disetujui.",
        data={"request_id": str(fund_request.id), "transaction_id": str(tx.id)}
    )

    log.info(
        "fund_request_approved",
        request_id=str(request_id),
        parent_id=str(parent.id),
        amount=str(fund_request.amount),
    )
    return FundRequestResponse.model_validate(fund_request)


async def reject_request(
    request_id: uuid.UUID,
    parent: User,
    db: AsyncSession,
) -> FundRequestResponse:
    """Parent rejects fund request. No wallet changes."""
    if parent.role != "parent":
        raise ForbiddenException(
            code="PARENT_ROLE_REQUIRED",
            message="Hanya parent yang bisa menolak fund request.",
        )

    fund_request = await db.get(FundRequest, request_id)
    if not fund_request:
        raise NotFoundException(resource="FundRequest")

    # Verify parent is in the same family
    membership = await db.scalar(
        select(FamilyMember).where(
            FamilyMember.user_id == parent.id,
            FamilyMember.family_id == fund_request.family_id,
            FamilyMember.is_active == True,  # noqa: E712
        )
    )
    if not membership:
        raise ForbiddenException(
            code="NOT_FAMILY_MEMBER",
            message="Anda tidak memiliki akses ke fund request ini.",
        )

    # Only pending can be rejected
    if fund_request.status != FundRequestStatus.PENDING:
        raise BadRequestException(
            code="INVALID_STATE_TRANSITION",
            message=f"Tidak bisa reject fund request dengan status '{fund_request.status}'.",
        )

    fund_request.status = FundRequestStatus.REJECTED
    fund_request.parent_id = parent.id
    fund_request.reviewed_at = datetime.now(UTC)
    db.add(fund_request)
    await db.flush()
    await db.refresh(fund_request)

    from app.services.notification_service import create_notification
    # Notify child
    await create_notification(
        session=db,
        user_id=fund_request.child_id,
        type=NotificationType.FUND_REQUEST_REJECTED,
        title="Permintaan Dana Ditolak",
        message=f"Permintaan dana sebesar {fund_request.amount} {fund_request.currency} telah ditolak.",
        data={"request_id": str(fund_request.id)}
    )

    log.info("fund_request_rejected", request_id=str(request_id), parent_id=str(parent.id))
    return FundRequestResponse.model_validate(fund_request)
