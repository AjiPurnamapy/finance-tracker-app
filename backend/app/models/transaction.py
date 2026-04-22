"""
Transaction model — immutable financial ledger.

KRUSIAL: Transaction TIDAK punya updated_at dan TIDAK BOLEH di-update
atau di-delete setelah dibuat. Ini adalah prinsip immutable ledger.

Setiap transfer uang (task reward, allowance, dll) menghasilkan
SATU record transaction yang permanent.

reference_type + reference_id memungkinkan link ke sumber transaksi
(task, allowance, fund_request, dll) tanpa FK constraint langsung.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DECIMAL,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import Currency, TransactionType
from app.models.base import Base


class Transaction(Base):
    """
    Inherits from Base (not BaseModel) — deliberately NO updated_at.
    Once created, a transaction is immutable.
    """
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )

    # ------------------------------------------------------------------ #
    # Scope
    # ------------------------------------------------------------------ #
    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("families.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Wallet parties (nullable: e.g. system-generated allowance has no source)
    # ------------------------------------------------------------------ #
    source_wallet_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("wallets.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    destination_wallet_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("wallets.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Amount
    # ------------------------------------------------------------------ #
    amount: Mapped[Decimal] = mapped_column(
        DECIMAL(12, 2), nullable=False
    )
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency", create_type=True),
        nullable=False,
    )

    # ------------------------------------------------------------------ #
    # Metadata
    # ------------------------------------------------------------------ #
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, name="transactiontype", create_type=True),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)

    # Polymorphic reference to source entity (task_id, allowance_id, etc.)
    reference_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, nullable=True
    )

    # ------------------------------------------------------------------ #
    # Timestamp (created_at ONLY — immutable record)
    # ------------------------------------------------------------------ #
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ------------------------------------------------------------------ #
    # Relationships (read-only)
    # ------------------------------------------------------------------ #
    family: Mapped["Family"] = relationship(  # noqa: F821
        "Family",
        lazy="noload",
    )
    source_wallet: Mapped["Wallet | None"] = relationship(  # noqa: F821
        "Wallet",
        foreign_keys=[source_wallet_id],
        lazy="noload",
    )
    destination_wallet: Mapped["Wallet | None"] = relationship(  # noqa: F821
        "Wallet",
        foreign_keys=[destination_wallet_id],
        lazy="noload",
    )

    # ------------------------------------------------------------------ #
    # Indexes
    # ------------------------------------------------------------------ #
    __table_args__ = (
        # Family timeline (most recent first)
        Index("ix_transactions_family_created", "family_id", "created_at"),
        # Per-wallet history
        Index("ix_transactions_dest_wallet_created", "destination_wallet_id", "created_at"),
        Index("ix_transactions_src_wallet_created", "source_wallet_id", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} type={self.type} "
            f"amount={self.amount} {self.currency}>"
        )
