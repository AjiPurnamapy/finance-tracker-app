from sqlalchemy import String, ForeignKey, DECIMAL, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class SavingsGoal(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "savings_goals"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_amount: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    current_amount: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0.00)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
