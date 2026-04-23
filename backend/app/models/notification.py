from sqlalchemy import String, ForeignKey, Boolean, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from typing import Any

from app.models.base import Base, UUIDMixin, TimestampMixin


class Notification(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notifications"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # We use String to avoid PostgreSQL Enum migration issues, validated by Pydantic using NotificationType
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    data: Mapped[Any] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True) # Payload data for deep linking, e.g. {"task_id": "uuid"}
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_notifications_user_id_created_at", "user_id", "created_at"),
    )
