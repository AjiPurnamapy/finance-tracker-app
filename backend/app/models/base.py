"""
Base model classes — UUID primary key + automatic timestamps.
All SQLAlchemy models must inherit from Base.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Declarative base for all ORM models.
    Inherit from this to get SQLAlchemy 2.0 mapped_column support.
    """
    pass


class UUIDMixin:
    """UUID v4 primary key mixin."""
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        sort_order=-100,  # always first column
    )


class TimestampMixin:
    """
    Automatic created_at and updated_at timestamps.
    - created_at: set by DB on INSERT (server_default)
    - updated_at: set by DB on INSERT, updated on every UPDATE (onupdate)
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        sort_order=100,  # near last columns
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        sort_order=101,
    )


class BaseModel(UUIDMixin, TimestampMixin, Base):
    """
    Full base model that all regular entities inherit.
    Provides: UUID PK + created_at + updated_at.
    """
    __abstract__ = True

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}>"
