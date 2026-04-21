"""
Family & FamilyMember models.

families      — A family group created by a parent.
family_members — Junction: which users belong to which family.

Design notes:
- One parent can only own ONE family (enforced in service layer).
- A user can only be in ONE family at a time (enforced by unique
  constraint on (user_id) in the active-member query).
- Family admin = the parent who created it. Only admin can remove members.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import FamilyMemberRole
from app.models.base import Base, BaseModel


class Family(BaseModel):
    __tablename__ = "families"

    # ------------------------------------------------------------------ #
    # Core fields
    # ------------------------------------------------------------------ #
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # max_seats enforced at service layer via SUBSCRIPTION_MAX_SEATS constant
    max_seats: Mapped[int] = mapped_column(Integer, nullable=False, default=2)

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    creator: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[created_by],
        lazy="noload",
    )
    members: Mapped[list["FamilyMember"]] = relationship(
        "FamilyMember",
        back_populates="family",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    invitations: Mapped[list["Invitation"]] = relationship(  # noqa: F821
        "Invitation",
        back_populates="family",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Family id={self.id} name={self.name}>"


class FamilyMember(Base):
    """
    Inherits from Base (not BaseModel) — has its own joined_at instead
    of created_at/updated_at from the mixin (semantically cleaner).
    """
    __tablename__ = "family_members"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[FamilyMemberRole] = mapped_column(
        Enum(FamilyMemberRole, name="familymemberrole", create_type=True),
        nullable=False,
        default=FamilyMemberRole.MEMBER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    family: Mapped["Family"] = relationship(
        "Family",
        back_populates="members",
        lazy="noload",
    )
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        lazy="noload",
    )

    # ------------------------------------------------------------------ #
    # Indexes
    # ------------------------------------------------------------------ #
    __table_args__ = (
        # Enforce one active membership per user across all families
        Index("ix_family_members_user_active", "user_id", "is_active"),
        # Fast lookup: all active members of a family
        Index("ix_family_members_family_active", "family_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<FamilyMember family={self.family_id} user={self.user_id} role={self.role}>"
