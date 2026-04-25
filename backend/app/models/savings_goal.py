"""
Savings goal milik child — target tabungan dengan milestone tracking.

Design notes:
- Hanya child yang bisa membuat dan mengelola goal
- Contribution mendebit wallet child
- Milestone notifications dikirim di 25%, 50%, 75%, dan 100%
- Goal yang completed tidak bisa menerima contribution baru
"""

import uuid
from decimal import Decimal

from sqlalchemy import DECIMAL, Boolean, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class SavingsGoal(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "savings_goals"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(12, 2), nullable=False
    )
    current_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return (
            f"<SavingsGoal id={self.id} name={self.name!r} "
            f"{self.current_amount}/{self.target_amount} completed={self.is_completed}>"
        )
