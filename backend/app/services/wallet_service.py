"""
Wallet service — balance management with optimistic locking.

All balance operations use atomic UPDATE ... WHERE balance >= amount
to prevent race conditions without explicit transactions locks.
"""

import uuid
from decimal import Decimal

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import Currency
from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    InsufficientBalanceException,
    NotFoundException,
)
from app.models.family import FamilyMember
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.task import WalletResponse

log = structlog.get_logger(__name__)


async def get_wallet(user: User, db: AsyncSession) -> WalletResponse:
    """Return the calling user's wallet."""
    wallet = await _get_wallet_or_404(user.id, db)
    return WalletResponse.model_validate(wallet)


async def get_family_wallets(
    user: User,
    family_id: uuid.UUID,
    db: AsyncSession,
) -> list[WalletResponse]:
    """
    Parent only: return wallets for all active members of a family.
    Requester must be an admin of that family.
    """
    if user.role != "parent":
        raise ForbiddenException(
            code="PARENT_ROLE_REQUIRED",
            message="Hanya parent yang bisa melihat wallet anggota keluarga.",
        )

    # Verify requester is admin of the family
    membership = await db.scalar(
        select(FamilyMember).where(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == user.id,
            FamilyMember.is_active == True,  # noqa: E712
        )
    )
    if not membership:
        raise ForbiddenException(
            code="NOT_FAMILY_MEMBER",
            message="Anda bukan anggota family ini.",
        )

    # Get all active member user_ids in this family
    result = await db.execute(
        select(FamilyMember.user_id).where(
            FamilyMember.family_id == family_id,
            FamilyMember.is_active == True,  # noqa: E712
        )
    )
    member_ids = result.scalars().all()

    # Get wallets for all members
    wallets_result = await db.execute(
        select(Wallet).where(Wallet.user_id.in_(member_ids))
    )
    wallets = wallets_result.scalars().all()
    return [WalletResponse.model_validate(w) for w in wallets]


async def credit(
    wallet_id: uuid.UUID,
    amount: Decimal,
    currency: Currency,
    db: AsyncSession,
) -> None:
    """
    Add amount to wallet balance. Always succeeds (no floor limit for credits).
    Uses atomic UPDATE to avoid race conditions.
    """
    if amount <= 0:
        raise BadRequestException(
            code="INVALID_AMOUNT",
            message="Amount harus lebih dari 0.",
        )
    if currency == Currency.IDR:
        result = await db.execute(
            update(Wallet)
            .where(Wallet.id == wallet_id)
            .values(balance_idr=Wallet.balance_idr + amount)
        )
    else:
        result = await db.execute(
            update(Wallet)
            .where(Wallet.id == wallet_id)
            .values(balance_pts=Wallet.balance_pts + amount)
        )

    if result.rowcount == 0:
        raise NotFoundException(resource="Wallet")

    log.info(
        "wallet_credited",
        wallet_id=str(wallet_id),
        amount=str(amount),
        currency=currency,
    )


async def debit(
    wallet_id: uuid.UUID,
    amount: Decimal,
    currency: Currency,
    db: AsyncSession,
) -> None:
    """
    Subtract amount from wallet balance.
    Uses optimistic locking: WHERE balance >= amount.
    Raises InsufficientBalanceException if balance too low.
    """
    if amount <= 0:
        raise BadRequestException(
            code="INVALID_AMOUNT",
            message="Amount harus lebih dari 0.",
        )
    if currency == Currency.IDR:
        result = await db.execute(
            update(Wallet)
            .where(
                Wallet.id == wallet_id,
                Wallet.balance_idr >= amount,  # atomic check
            )
            .values(balance_idr=Wallet.balance_idr - amount)
        )
    else:
        result = await db.execute(
            update(Wallet)
            .where(
                Wallet.id == wallet_id,
                Wallet.balance_pts >= amount,  # atomic check
            )
            .values(balance_pts=Wallet.balance_pts - amount)
        )

    if result.rowcount == 0:
        raise InsufficientBalanceException(currency=currency)

    log.info(
        "wallet_debited",
        wallet_id=str(wallet_id),
        amount=str(amount),
        currency=currency,
    )


# ------------------------------------------------------------------ #
# Internal helpers
# ------------------------------------------------------------------ #

async def _get_wallet_or_404(user_id: uuid.UUID, db: AsyncSession) -> Wallet:
    wallet = await db.scalar(
        select(Wallet).where(Wallet.user_id == user_id)
    )
    if not wallet:
        raise NotFoundException(resource="Wallet")
    return wallet


async def get_wallet_by_user_id(user_id: uuid.UUID, db: AsyncSession) -> Wallet:
    """Helper used by other services to get wallet without permission checks."""
    return await _get_wallet_or_404(user_id, db)
