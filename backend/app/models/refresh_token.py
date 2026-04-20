"""
RefreshToken model — stores hashed refresh tokens.
Token itself is never stored in plain text (SHA-256 hashed).
Supports token rotation: old token is revoked when refreshed.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RefreshToken(Base):
    """
    NOTE: Inherits from Base (not BaseModel) because we do NOT want
    auto updated_at — refresh tokens are immutable once created.
    """
    __tablename__ = "refresh_tokens"

    # ------------------------------------------------------------------ #
    # PK & FK
    # ------------------------------------------------------------------ #
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Token data
    # ------------------------------------------------------------------ #
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    device_info: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="refresh_tokens",
        lazy="noload",
    )

    # ------------------------------------------------------------------ #
    # Composite index for efficient token lookup
    # ------------------------------------------------------------------ #
    __table_args__ = (
        Index("ix_refresh_tokens_user_active", "user_id", "is_revoked"),
    )

    def __repr__(self) -> str:
        return f"<RefreshToken id={self.id} user_id={self.user_id} revoked={self.is_revoked}>"
