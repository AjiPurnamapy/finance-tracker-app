"""
Expense model — pencatatan pengeluaran (opsional debit dari wallet).

Design notes:
- spent_at: tanggal transaksi aktual (bisa berbeda dari created_at)
- deduct_from_wallet: jika True, wallet user di-debit saat expense dibuat
- Expense yang sudah deduct wallet TIDAK bisa dihapus (financial integrity)
- transaction_id di-set jika deduct_from_wallet=True
- Currency MVP: IDR only
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DECIMAL,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import Currency, ExpenseCategory
from app.models.base import BaseModel


class Expense(BaseModel):
    __tablename__ = "expenses"

    # ------------------------------------------------------------------ #
    # Core identity
    # ------------------------------------------------------------------ #
    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Only set if deduct_from_wallet=True
    wallet_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("wallets.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ------------------------------------------------------------------ #
    # Expense details
    # ------------------------------------------------------------------ #
    amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency", create_type=False),
        nullable=False,
        default=Currency.IDR,
    )
    category: Mapped[ExpenseCategory] = mapped_column(
        Enum(ExpenseCategory, name="expensecategory", create_type=True),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Actual date of spending (may differ from created_at)
    spent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # ------------------------------------------------------------------ #
    # Financial tracking
    # ------------------------------------------------------------------ #
    # If True: wallet was debited when this expense was created
    deduct_from_wallet: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    # Reference to debit transaction (only if deduct_from_wallet=True)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    family: Mapped["Family"] = relationship("Family", lazy="noload")  # noqa: F821
    user: Mapped["User"] = relationship("User", lazy="noload")  # noqa: F821

    # ------------------------------------------------------------------ #
    # Indexes
    # ------------------------------------------------------------------ #
    __table_args__ = (
        # Family expense timeline (parent dashboard)
        Index("ix_expenses_family_spent_at", "family_id", "spent_at"),
        # User's own expenses by date
        Index("ix_expenses_user_spent_at", "user_id", "spent_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Expense user={self.user_id} amount={self.amount} "
            f"category={self.category} title={self.title!r}>"
        )
