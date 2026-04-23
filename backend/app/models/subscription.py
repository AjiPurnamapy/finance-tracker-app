from sqlalchemy import String, ForeignKey, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.models.base import Base, UUIDMixin, TimestampMixin


class Subscription(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "subscriptions"

    family_id: Mapped[str] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"), unique=True, index=True)
    tier: Mapped[str] = mapped_column(String(50), nullable=False, default="free") # Validated by SubscriptionTier
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active") # Validated by SubscriptionStatus
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    max_seats: Mapped[int] = mapped_column(Integer, default=2)
