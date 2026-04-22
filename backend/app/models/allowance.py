"""
Allowance model — konfigurasi uang saku dari parent ke child.

Design notes:
- Satu parent hanya bisa punya 1 allowance aktif per child (UniqueConstraint)
- is_recurring=True: dikirim periodik (daily/weekly/custom)
- is_recurring=False: one-time manual transfer
- next_payment_at: kapan transfer berikutnya dijadwalkan (MVP: manual trigger)
- Actual transfer dilakukan via allowance_service.manual_transfer()
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
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import Currency, RecurrenceType
from app.models.base import BaseModel


class Allowance(BaseModel):
    __tablename__ = "allowances"

    # ------------------------------------------------------------------ #
    # Core identity
    # ------------------------------------------------------------------ #
    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Allowance configuration
    # ------------------------------------------------------------------ #
    amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency", create_type=False),
        nullable=False,
        default=Currency.IDR,
    )

    # Scheduling
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    recurrence_type: Mapped[RecurrenceType | None] = mapped_column(
        Enum(RecurrenceType, name="recurrencetype", create_type=False),
        nullable=True,
    )
    # MVP: manual trigger only. Future: background job reads this field.
    next_payment_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Soft toggle — parent bisa nonaktifkan tanpa hapus
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    family: Mapped["Family"] = relationship("Family", lazy="noload")  # noqa: F821
    parent: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[parent_id], lazy="noload"
    )
    child: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[child_id], lazy="noload"
    )

    # ------------------------------------------------------------------ #
    # Indexes + Constraints
    # ------------------------------------------------------------------ #
    __table_args__ = (
        # One active allowance config per parent-child pair
        UniqueConstraint("parent_id", "child_id", name="uq_allowance_parent_child"),
        # Composite index for background job: find due allowances
        Index("ix_allowances_active_next_payment", "is_active", "next_payment_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Allowance parent={self.parent_id} child={self.child_id} "
            f"amount={self.amount} {self.currency} active={self.is_active}>"
        )
