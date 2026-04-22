"""
Allowance service — manajemen uang saku dari parent ke child.

Business rules:
- Satu parent hanya bisa punya 1 allowance per child (unique constraint)
- manual_transfer: debit parent wallet → credit child wallet → buat transaksi
- MVP: tidak ada scheduler otomatis (transfer dilakukan manual)
"""

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import Currency, TransactionType
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.models.allowance import Allowance
from app.models.family import FamilyMember
from app.models.user import User
from app.schemas.allowance import AllowanceResponse, CreateAllowanceRequest, UpdateAllowanceRequest
from app.schemas.task import TransactionResponse

log = structlog.get_logger(__name__)


async def _get_user_family(user: User, db: AsyncSession) -> FamilyMember:
    """Get active family membership or raise NotFoundException."""
    membership = await db.scalar(
        select(FamilyMember).where(
            FamilyMember.user_id == user.id,
            FamilyMember.is_active == True,  # noqa: E712
        )
    )
    if not membership:
        raise NotFoundException(resource="Family", code="NOT_IN_FAMILY")
    return membership


async def create_allowance(
    parent: User,
    data: CreateAllowanceRequest,
    db: AsyncSession,
) -> AllowanceResponse:
    """
    Parent creates allowance config for a child in the same family.
    Raises 409 if allowance already exists for this parent-child pair.
    """
    if parent.role != "parent":
        raise ForbiddenException(
            code="PARENT_ROLE_REQUIRED",
            message="Hanya parent yang bisa membuat allowance.",
        )

    # Verify parent is in a family
    membership = await _get_user_family(parent, db)
    family_id = membership.family_id

    # Verify target child is in the same family
    child_membership = await db.scalar(
        select(FamilyMember).where(
            FamilyMember.user_id == data.child_id,
            FamilyMember.family_id == family_id,
            FamilyMember.is_active == True,  # noqa: E712
        )
    )
    if not child_membership:
        raise ForbiddenException(
            code="CHILD_NOT_IN_FAMILY",
            message="Child bukan anggota keluarga yang sama.",
        )

    # Check child is actually a child role
    from app.models.user import User as UserModel
    child_user = await db.get(UserModel, data.child_id)
    if not child_user or child_user.role != "child":
        raise ForbiddenException(
            code="TARGET_NOT_CHILD",
            message="Allowance hanya bisa dibuat untuk user berperan child.",
        )

    # Check uniqueness — one allowance per parent-child pair
    existing = await db.scalar(
        select(Allowance).where(
            Allowance.parent_id == parent.id,
            Allowance.child_id == data.child_id,
        )
    )
    if existing:
        raise ConflictException(
            code="ALLOWANCE_ALREADY_EXISTS",
            message="Allowance untuk child ini sudah ada. Gunakan PATCH untuk mengubahnya.",
        )

    allowance = Allowance(
        family_id=family_id,
        parent_id=parent.id,
        child_id=data.child_id,
        amount=data.amount,
        currency=data.currency,
        is_recurring=data.is_recurring,
        recurrence_type=data.recurrence_type,
        next_payment_at=data.next_payment_at,
        is_active=True,
    )
    db.add(allowance)
    await db.flush()
    await db.refresh(allowance)

    log.info("allowance_created", allowance_id=str(allowance.id), parent_id=str(parent.id), child_id=str(data.child_id))
    return AllowanceResponse.model_validate(allowance)


async def list_allowances(user: User, db: AsyncSession) -> list[AllowanceResponse]:
    """
    Parent: all allowances they created.
    Child: only allowances assigned to them.
    """
    if user.role == "parent":
        result = await db.execute(
            select(Allowance).where(Allowance.parent_id == user.id)
        )
    else:
        result = await db.execute(
            select(Allowance).where(Allowance.child_id == user.id)
        )
    allowances = result.scalars().all()
    return [AllowanceResponse.model_validate(a) for a in allowances]


async def get_allowance(
    allowance_id: uuid.UUID,
    user: User,
    db: AsyncSession,
) -> AllowanceResponse:
    """Get allowance by id. User must be parent or the assigned child."""
    allowance = await db.get(Allowance, allowance_id)
    if not allowance:
        raise NotFoundException(resource="Allowance")

    if user.id not in (allowance.parent_id, allowance.child_id):
        raise ForbiddenException(
            code="NOT_ALLOWANCE_OWNER",
            message="Anda tidak memiliki akses ke allowance ini.",
        )
    return AllowanceResponse.model_validate(allowance)


async def update_allowance(
    allowance_id: uuid.UUID,
    parent: User,
    data: UpdateAllowanceRequest,
    db: AsyncSession,
) -> AllowanceResponse:
    """Parent updates allowance. Only the creating parent can update."""
    if parent.role != "parent":
        raise ForbiddenException(
            code="PARENT_ROLE_REQUIRED",
            message="Hanya parent yang bisa mengubah allowance.",
        )

    allowance = await db.get(Allowance, allowance_id)
    if not allowance:
        raise NotFoundException(resource="Allowance")

    if allowance.parent_id != parent.id:
        raise ForbiddenException(
            code="NOT_ALLOWANCE_OWNER",
            message="Anda bukan pemilik allowance ini.",
        )

    fields_sent = data.model_fields_set
    if "amount" in fields_sent and data.amount is not None:
        allowance.amount = data.amount
    if "currency" in fields_sent and data.currency is not None:
        allowance.currency = data.currency
    if "is_recurring" in fields_sent and data.is_recurring is not None:
        allowance.is_recurring = data.is_recurring
    if "recurrence_type" in fields_sent:
        allowance.recurrence_type = data.recurrence_type
    if "next_payment_at" in fields_sent:
        allowance.next_payment_at = data.next_payment_at
    if "is_active" in fields_sent and data.is_active is not None:
        allowance.is_active = data.is_active

    db.add(allowance)
    await db.flush()
    await db.refresh(allowance)
    return AllowanceResponse.model_validate(allowance)


async def manual_transfer(
    allowance_id: uuid.UUID,
    parent: User,
    db: AsyncSession,
) -> TransactionResponse:
    """
    Parent manually triggers allowance transfer.
    Debit parent wallet → credit child wallet → record transaction.

    IMPORTANT: All operations within single DB transaction from get_db().
    If any step fails, everything is rolled back.
    """
    from app.services import transaction_service, wallet_service

    if parent.role != "parent":
        raise ForbiddenException(
            code="PARENT_ROLE_REQUIRED",
            message="Hanya parent yang bisa mentransfer allowance.",
        )

    allowance = await db.get(Allowance, allowance_id)
    if not allowance:
        raise NotFoundException(resource="Allowance")
    if allowance.parent_id != parent.id:
        raise ForbiddenException(
            code="NOT_ALLOWANCE_OWNER",
            message="Anda bukan pemilik allowance ini.",
        )
    if not allowance.is_active:
        raise ForbiddenException(
            code="ALLOWANCE_INACTIVE",
            message="Allowance tidak aktif.",
        )

    # Get wallets
    parent_wallet = await wallet_service.get_wallet_by_user_id(parent.id, db)
    child_wallet = await wallet_service.get_wallet_by_user_id(allowance.child_id, db)

    # Debit parent (raises InsufficientBalanceException if not enough)
    # NOTE: parent_wallet object becomes stale after debit — do not read balance from it.
    await wallet_service.debit(
        wallet_id=parent_wallet.id,
        amount=allowance.amount,
        currency=allowance.currency,
        db=db,
    )

    # Credit child
    # NOTE: child_wallet object becomes stale after credit.
    await wallet_service.credit(
        wallet_id=child_wallet.id,
        amount=allowance.amount,
        currency=allowance.currency,
        db=db,
    )

    # Record immutable transaction
    tx = await transaction_service.create_transaction(
        family_id=allowance.family_id,
        source_wallet_id=parent_wallet.id,
        destination_wallet_id=child_wallet.id,
        amount=allowance.amount,
        currency=allowance.currency,
        type=TransactionType.ALLOWANCE,
        description=f"Allowance transfer dari parent ke child",
        reference_type="allowance",
        reference_id=allowance.id,
        db=db,
    )

    log.info(
        "allowance_transferred",
        allowance_id=str(allowance_id),
        amount=str(allowance.amount),
        currency=allowance.currency,
    )
    from app.schemas.task import TransactionResponse
    return TransactionResponse.model_validate(tx)
