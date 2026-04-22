"""
Transaction service — immutable ledger operations.

Transactions are append-only. No updates, no deletes.
"""

import uuid
from decimal import Decimal

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import Currency, TransactionType
from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.family import FamilyMember
from app.models.transaction import Transaction
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.task import TransactionResponse

log = structlog.get_logger(__name__)


async def create_transaction(
    *,
    family_id: uuid.UUID,
    source_wallet_id: uuid.UUID | None,
    destination_wallet_id: uuid.UUID | None,
    amount: Decimal,
    currency: Currency,
    type: TransactionType,
    description: str,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
    db: AsyncSession,
) -> Transaction:
    """
    Create an immutable transaction record.
    This is the ONLY way to record financial movements.
    """
    tx = Transaction(
        family_id=family_id,
        source_wallet_id=source_wallet_id,
        destination_wallet_id=destination_wallet_id,
        amount=amount,
        currency=currency,
        type=type,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(tx)
    await db.flush()

    log.info(
        "transaction_created",
        tx_id=str(tx.id),
        type=type,
        amount=str(amount),
        currency=currency,
    )
    return tx


async def list_transactions(
    user: User,
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[TransactionResponse], int]:
    """
    List transactions scoped to the user's family.
    Parent sees all family transactions.
    Child sees only transactions involving their own wallet.
    """
    # Get user's family membership
    membership = await db.scalar(
        select(FamilyMember).where(
            FamilyMember.user_id == user.id,
            FamilyMember.is_active == True,  # noqa: E712
        )
    )
    if not membership:
        raise NotFoundException(resource="Family", code="NOT_IN_FAMILY")

    family_id = membership.family_id

    if user.role == "parent":
        # Parent sees all family transactions
        base_query = select(Transaction).where(
            Transaction.family_id == family_id
        )
    else:
        # Child sees only their own wallet transactions
        wallet = await db.scalar(
            select(Wallet).where(Wallet.user_id == user.id)
        )
        if not wallet:
            raise NotFoundException(resource="Wallet")
        base_query = select(Transaction).where(
            Transaction.family_id == family_id,
            (Transaction.destination_wallet_id == wallet.id)
            | (Transaction.source_wallet_id == wallet.id),
        )

    # Count total
    count_result = await db.scalar(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result or 0

    # Paginate
    offset = (page - 1) * per_page
    result = await db.execute(
        base_query.order_by(Transaction.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    transactions = result.scalars().all()

    return [TransactionResponse.model_validate(tx) for tx in transactions], total


async def get_transaction(
    transaction_id: uuid.UUID,
    user: User,
    db: AsyncSession,
) -> TransactionResponse:
    """Get a specific transaction. User must be in same family."""
    tx = await db.get(Transaction, transaction_id)
    if not tx:
        raise NotFoundException(resource="Transaction")

    # Verify user is in this family
    membership = await db.scalar(
        select(FamilyMember).where(
            FamilyMember.user_id == user.id,
            FamilyMember.family_id == tx.family_id,
            FamilyMember.is_active == True,  # noqa: E712
        )
    )
    if not membership:
        raise ForbiddenException(
            code="NOT_FAMILY_MEMBER",
            message="Anda tidak memiliki akses ke transaksi ini.",
        )

    return TransactionResponse.model_validate(tx)
