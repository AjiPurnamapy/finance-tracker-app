"""
Subscription langganan per family.

Design notes:
- tier dan status menggunakan String (bukan Enum) untuk fleksibilitas.
  Validasi dilakukan di Pydantic layer via SubscriptionTier/SubscriptionStatus.
- Satu family hanya punya satu subscription (unique constraint pada family_id).
- MVP: tidak ada payment gateway, upgrade/cancel langsung ke DB.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class Subscription(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "subscriptions"

    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    tier: Mapped[str] = mapped_column(String(50), nullable=False, default="free")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    max_seats: Mapped[int] = mapped_column(Integer, nullable=False, default=2)

    def __repr__(self) -> str:
        return f"<Subscription family={self.family_id} tier={self.tier} status={self.status}>"
