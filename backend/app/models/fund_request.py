"""
FundRequest model — permintaan dana dari child ke parent.

State machine:
  pending → approved  (parent approve → wallet transfer executed)
  pending → rejected  (parent reject → no transfer)

Design notes:
- Hanya pending request yang bisa di-review
- transaction_id di-set setelah approval (FK nullable)
- reviewed_at + parent_id di-set saat review
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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import Currency, FundRequestStatus, FundRequestType
from app.models.base import BaseModel


class FundRequest(BaseModel):
    __tablename__ = "fund_requests"

    # ------------------------------------------------------------------ #
    # Core identity
    # ------------------------------------------------------------------ #
    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Set saat parent review
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ------------------------------------------------------------------ #
    # Request details
    # ------------------------------------------------------------------ #
    amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency", create_type=False),
        nullable=False,
        default=Currency.IDR,
    )
    type: Mapped[FundRequestType] = mapped_column(
        Enum(FundRequestType, name="fundrequesttype", create_type=False),
        nullable=False,
        default=FundRequestType.ONE_TIME,
    )
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ------------------------------------------------------------------ #
    # State machine
    # ------------------------------------------------------------------ #
    status: Mapped[FundRequestStatus] = mapped_column(
        Enum(FundRequestStatus, name="fundrequeststatus", create_type=False),
        nullable=False,
        default=FundRequestStatus.PENDING,
        index=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Reference to the generated transaction (only when approved)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    family: Mapped["Family"] = relationship("Family", lazy="noload")  # noqa: F821
    child: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[child_id], lazy="noload"
    )
    reviewer: Mapped["User | None"] = relationship(  # noqa: F821
        "User", foreign_keys=[parent_id], lazy="noload"
    )

    # ------------------------------------------------------------------ #
    # Indexes
    # ------------------------------------------------------------------ #
    __table_args__ = (
        # Parent view: all requests by family + status
        Index("ix_fund_requests_family_status", "family_id", "status"),
        # Child view: own requests by status
        Index("ix_fund_requests_child_status", "child_id", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<FundRequest child={self.child_id} amount={self.amount} "
            f"{self.currency} status={self.status}>"
        )
