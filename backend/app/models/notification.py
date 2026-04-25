"""
Notifikasi sistem untuk user.

Design notes:
- type menggunakan String (bukan Enum) untuk menghindari PostgreSQL
  migration complexity. Validasi dilakukan di Pydantic layer.
- data berisi payload untuk deep linking (misal: task_id, goal_id)
"""

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, String, Uuid, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class Notification(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    data: Mapped[Any] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_notifications_user_id_created_at", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Notification id={self.id} user={self.user_id} type={self.type} read={self.is_read}>"
