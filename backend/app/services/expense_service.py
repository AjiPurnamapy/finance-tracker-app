"""
Expense service — pencatatan pengeluaran.

Business rules:
- spent_at default ke now() jika tidak dikirim
- deduct_from_wallet=True: wallet user di-debit saat dibuat
- Expense yang sudah deduct wallet TIDAK bisa dihapus (financial integrity)
- Currency MVP: IDR only
- Parent bisa lihat semua expense family, child hanya melihat milik sendiri
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import Currency, ExpenseCategory, TransactionType
from app.core.exceptions import (
    ForbiddenException,
    NotFoundException,
)
from app.models.expense import Expense
from app.models.family import FamilyMember
from app.models.user import User
from app.schemas.expense import (
    CreateExpenseRequest,
    ExpenseCategoryInfo,
    ExpenseResponse,
    UpdateExpenseRequest,
)
from app.services.common import get_active_family_membership

log = structlog.get_logger(__name__)


async def create_expense(
    user: User,
    data: CreateExpenseRequest,
    db: AsyncSession,
) -> ExpenseResponse:
    """
    Create expense record.
    If deduct_from_wallet=True: debit user wallet and create transaction.
    """
    from app.services import transaction_service, wallet_service

    # Verify user is in a family
    membership = await get_active_family_membership(user, db)

    spent_at = data.spent_at or datetime.now(UTC)
    wallet_id: uuid.UUID | None = None
    tx_id: uuid.UUID | None = None

    if data.deduct_from_wallet:
        # Debit user's wallet
        user_wallet = await wallet_service.get_wallet_by_user_id(user.id, db)
        wallet_id = user_wallet.id

        # NOTE: wallet object becomes stale after debit.
        await wallet_service.debit(
            wallet_id=user_wallet.id,
            amount=data.amount,
            currency=data.currency,
            db=db,
        )

        # Create immutable transaction record
        tx = await transaction_service.create_transaction(
            family_id=membership.family_id,
            source_wallet_id=user_wallet.id,
            destination_wallet_id=None,
            amount=data.amount,
            currency=data.currency,
            type=TransactionType.EXPENSE,
            description=f"Expense: {data.title}",
            reference_type="expense",
            reference_id=None,  # set after expense insert
            db=db,
        )
        tx_id = tx.id

    expense = Expense(
        family_id=membership.family_id,
        user_id=user.id,
        wallet_id=wallet_id,
        amount=data.amount,
        currency=data.currency,
        category=data.category,
        title=data.title,
        description=data.description,
        spent_at=spent_at,
        deduct_from_wallet=data.deduct_from_wallet,
        transaction_id=tx_id,
    )
    db.add(expense)
    await db.flush()
    await db.refresh(expense)

    log.info(
        "expense_created",
        expense_id=str(expense.id),
        user_id=str(user.id),
        amount=str(data.amount),
        deducted=data.deduct_from_wallet,
    )
    return ExpenseResponse.model_validate(expense)


async def list_expenses(
    user: User,
    db: AsyncSession,
    category: ExpenseCategory | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[ExpenseResponse], int]:
    """
    Parent: all expenses in family.
    Child: only own expenses.
    Filter by category optional.
    """
    membership = await get_active_family_membership(user, db)
    family_id = membership.family_id

    if user.role == "parent":
        base_query = select(Expense).where(Expense.family_id == family_id)
    else:
        base_query = select(Expense).where(Expense.user_id == user.id)

    if category:
        base_query = base_query.where(Expense.category == category)

    total = await db.scalar(
        select(func.count()).select_from(base_query.subquery())
    ) or 0

    offset = (page - 1) * per_page
    result = await db.execute(
        base_query.order_by(Expense.spent_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    expenses = result.scalars().all()
    return [ExpenseResponse.model_validate(e) for e in expenses], total


async def get_expense(
    expense_id: uuid.UUID,
    user: User,
    db: AsyncSession,
) -> ExpenseResponse:
    """Get expense. User must be in same family."""
    expense = await db.get(Expense, expense_id)
    if not expense:
        raise NotFoundException(resource="Expense")

    membership = await db.scalar(
        select(FamilyMember).where(
            FamilyMember.user_id == user.id,
            FamilyMember.family_id == expense.family_id,
            FamilyMember.is_active == True,  # noqa: E712
        )
    )
    if not membership:
        raise ForbiddenException(
            code="NOT_FAMILY_MEMBER",
            message="Anda tidak memiliki akses ke expense ini.",
        )
    return ExpenseResponse.model_validate(expense)


async def update_expense(
    expense_id: uuid.UUID,
    user: User,
    data: UpdateExpenseRequest,
    db: AsyncSession,
) -> ExpenseResponse:
    """Only the owner can update. Only non-financial fields."""
    expense = await db.get(Expense, expense_id)
    if not expense:
        raise NotFoundException(resource="Expense")
    if expense.user_id != user.id:
        raise ForbiddenException(
            code="NOT_EXPENSE_OWNER",
            message="Anda bukan pemilik expense ini.",
        )

    fields_sent = data.model_fields_set
    if "category" in fields_sent and data.category is not None:
        expense.category = data.category
    if "title" in fields_sent and data.title is not None:
        expense.title = data.title.strip()
    if "description" in fields_sent:
        expense.description = data.description
    if "spent_at" in fields_sent and data.spent_at is not None:
        expense.spent_at = data.spent_at

    db.add(expense)
    await db.flush()
    await db.refresh(expense)
    return ExpenseResponse.model_validate(expense)


async def delete_expense(
    expense_id: uuid.UUID,
    user: User,
    db: AsyncSession,
) -> None:
    """
    Delete expense. Only owner can delete.
    Expenses that deducted wallet CANNOT be deleted (financial integrity).
    """
    expense = await db.get(Expense, expense_id)
    if not expense:
        raise NotFoundException(resource="Expense")
    if expense.user_id != user.id:
        raise ForbiddenException(
            code="NOT_EXPENSE_OWNER",
            message="Anda bukan pemilik expense ini.",
        )
    if expense.deduct_from_wallet:
        raise ForbiddenException(
            code="EXPENSE_FINANCIAL_RECORD",
            message="Expense yang sudah memotong wallet tidak bisa dihapus.",
        )

    await db.delete(expense)
    await db.flush()
    log.info("expense_deleted", expense_id=str(expense_id), user_id=str(user.id))


def get_categories() -> list[ExpenseCategoryInfo]:
    """Return all available expense categories with human-readable labels."""
    return ExpenseCategoryInfo.all()
