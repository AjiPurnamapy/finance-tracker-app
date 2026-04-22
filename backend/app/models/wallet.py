"""
Wallet model — setiap user punya tepat satu wallet.

Dibuat otomatis saat user register (via auth_service).
Menyimpan saldo IDR dan PTS secara terpisah.

Design notes:
- DECIMAL(12, 2) untuk IDR → max ~10 miliar IDR
- DECIMAL(12, 2) untuk PTS → max ~10 miliar PTS
- Unique constraint pada user_id memastikan 1 user = 1 wallet
- Optimistic lock via UPDATE ... WHERE balance >= amount (di wallet_service)
"""

import uuid
from decimal import Decimal

from sqlalchemy import DECIMAL, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Wallet(BaseModel):
    __tablename__ = "wallets"

    # ------------------------------------------------------------------ #
    # Core fields
    # ------------------------------------------------------------------ #
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,   # 1 user = 1 wallet
        index=True,
    )

    # IDR balance — rupiah
    balance_idr: Mapped[Decimal] = mapped_column(
        DECIMAL(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    # PTS balance — poin reward
    balance_pts: Mapped[Decimal] = mapped_column(
        DECIMAL(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Wallet user={self.user_id} idr={self.balance_idr} pts={self.balance_pts}>"
