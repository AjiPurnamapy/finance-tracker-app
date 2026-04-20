"""
User model — core identity entity.
Every user has exactly one wallet (created at registration).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import UserRole
from app.models.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    # ------------------------------------------------------------------ #
    # Core fields
    # ------------------------------------------------------------------ #
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ------------------------------------------------------------------ #
    # Role & status
    # ------------------------------------------------------------------ #
    role: Mapped[str] = mapped_column(
        Enum(UserRole, name="userrole", create_type=True),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ------------------------------------------------------------------ #
    # Relationships (defined here; back-populated in related models)
    # ------------------------------------------------------------------ #
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(  # noqa: F821
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
