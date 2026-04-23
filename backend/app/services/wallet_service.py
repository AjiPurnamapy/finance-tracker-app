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


async def topup(
    user: User,
    amount: Decimal,
    description: str | None,
    db: AsyncSession,
) -> "WalletResponse":
    """
    Parent top-up their own IDR wallet.
    MVP: no payment gateway — direct credit.
    Parent-only operation.
    """
    from app.models.user import User as UserModel
    from app.services import transaction_service
    from app.core.constants import TransactionType
    from app.models.family import FamilyMember
    from sqlalchemy import select as sa_select

    if user.role != "parent":
        raise ForbiddenException(
            code="PARENT_ROLE_REQUIRED",
            message="Hanya parent yang bisa melakukan top-up wallet.",
        )
    if amount <= 0:
        raise BadRequestException(
            code="INVALID_AMOUNT",
            message="Amount harus lebih dari 0.",
        )

    wallet = await _get_wallet_or_404(user.id, db)

    # Get family_id for transaction record
    membership = await db.scalar(
        sa_select(FamilyMember).where(
            FamilyMember.user_id == user.id,
            FamilyMember.is_active == True,  # noqa: E712
        )
    )

    await credit(wallet_id=wallet.id, amount=amount, currency=Currency.IDR, db=db)

    # Record top-up as a transaction if in a family
    if membership:
        await transaction_service.create_transaction(
            family_id=membership.family_id,
            source_wallet_id=None,
            destination_wallet_id=wallet.id,
            amount=amount,
            currency=Currency.IDR,
            type=TransactionType.TOPUP,
            description=description or "Wallet top-up",
            db=db,
        )

    # Refresh to get updated balance
    await db.refresh(wallet)
    log.info("wallet_topup", user_id=str(user.id), amount=str(amount))
    return WalletResponse.model_validate(wallet)


async def exchange_pts(
    user: User,
    pts_amount: Decimal,
    db: AsyncSession,
) -> "ExchangePtsResponse":
    """
    Exchange user's PTS to IDR based on active exchange rate.

    Business rules:
    - Minimum 100 PTS, must be multiple of 100
    - Rate: X PTS = Y IDR (from pts_exchange_rates table)
    - IDR credited = (pts_amount / rate.pts_amount) * rate.idr_amount
    - Atomic: PTS debited and IDR credited in same DB transaction

    IMPORTANT: All operations within single DB transaction from get_db().
    """
    from sqlalchemy import select as sa_select
    from app.models.pts_exchange_rate import PtsExchangeRate
    from app.models.family import FamilyMember
    from app.services import transaction_service
    from app.core.constants import TransactionType
    from app.schemas.wallet import ExchangePtsResponse

    if pts_amount <= 0:
        raise BadRequestException(
            code="INVALID_AMOUNT",
            message="pts_amount harus lebih dari 0.",
        )
    if pts_amount < 100:
        raise BadRequestException(
            code="BELOW_MINIMUM_EXCHANGE",
            message="Minimum exchange adalah 100 PTS.",
        )
    if pts_amount % 100 != 0:
        raise BadRequestException(
            code="NOT_MULTIPLE_OF_100",
            message="pts_amount harus kelipatan 100.",
        )

    # Fetch active exchange rate with row lock to prevent race conditions
    rate = await db.scalar(
        sa_select(PtsExchangeRate).where(PtsExchangeRate.is_active == True).with_for_update()  # noqa: E712
    )
    if not rate:
        raise NotFoundException(resource="PtsExchangeRate", code="NO_ACTIVE_RATE")

    # Calculate IDR equivalent
    idr_credited = (pts_amount / rate.pts_amount) * rate.idr_amount

    # Get user wallet
    wallet = await _get_wallet_or_404(user.id, db)

    # Get family for transaction record
    membership = await db.scalar(
        sa_select(FamilyMember).where(
            FamilyMember.user_id == user.id,
            FamilyMember.is_active == True,  # noqa: E712
        )
    )

    # Debit PTS (raises InsufficientBalanceException if not enough)
    # NOTE: wallet object becomes stale after debit.
    await debit(wallet_id=wallet.id, amount=pts_amount, currency=Currency.PTS, db=db)

    # Credit IDR
    await credit(wallet_id=wallet.id, amount=idr_credited, currency=Currency.IDR, db=db)

    # Record transaction if in a family
    if membership:
        await transaction_service.create_transaction(
            family_id=membership.family_id,
            source_wallet_id=wallet.id,
            destination_wallet_id=wallet.id,
            amount=pts_amount,
            currency=Currency.PTS,
            type=TransactionType.PTS_EXCHANGE,
            description=f"PTS exchange: {pts_amount} PTS → Rp {idr_credited:,.2f}",
            db=db,
        )

    # Refresh wallet to get updated balances
    await db.refresh(wallet)

    log.info(
        "pts_exchanged",
        user_id=str(user.id),
        pts_deducted=str(pts_amount),
        idr_credited=str(idr_credited),
    )

    return ExchangePtsResponse(
        pts_deducted=pts_amount,
        idr_credited=idr_credited,
        rate_pts=rate.pts_amount,
        rate_idr=rate.idr_amount,
        new_balance_pts=wallet.balance_pts,
        new_balance_idr=wallet.balance_idr,
    )
