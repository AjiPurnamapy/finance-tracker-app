"""
PtsExchangeRate model — konfigurasi rate tukar PTS ke IDR.

Design notes:
- Hanya SATU rate yang aktif (is_active=True) pada satu waktu
- Default: 1000 PTS = Rp 10.000 (seeded via migration)
- Constraint ini dijaga di service layer (bukan DB constraint)
- MVP: admin bisa update rate di future (Phase 7)
"""

import uuid
from decimal import Decimal

from sqlalchemy import DECIMAL, Boolean, ForeignKey, Uuid, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class PtsExchangeRate(BaseModel):
    __tablename__ = "pts_exchange_rates"

    # ------------------------------------------------------------------ #
    # Rate configuration
    # ------------------------------------------------------------------ #
    # How many PTS to exchange
    pts_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(12, 2), nullable=False
    )
    # How much IDR the above PTS amount equals
    idr_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(12, 2), nullable=False
    )

    # Only one rate should be active at any time (enforced in service)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )

    # Who created/updated this rate (nullable: seeded by migration)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    creator: Mapped["User | None"] = relationship(  # noqa: F821
        "User", lazy="noload"
    )

    # ------------------------------------------------------------------ #
    # Indexes + Constraints
    # ------------------------------------------------------------------ #
    __table_args__ = (
        Index(
            "ix_pts_exchange_rates_active",
            "is_active",
            unique=True,
            sqlite_where=text("is_active = 1"),
            postgresql_where=text("is_active = true")
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<PtsExchangeRate {self.pts_amount} PTS = "
            f"Rp {self.idr_amount} active={self.is_active}>"
        )
