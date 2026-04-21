"""
Invitation model — stores invite codes for joining a family.

Invite code: 6-digit numeric string (000000–999999), UNIQUE, INDEX.
Lifecycle: sent → accepted | expired | cancelled
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import InvitationStatus
from app.models.base import Base


class Invitation(Base):
    """
    Inherits from Base (not BaseModel) — immutable once accepted,
    no need for updated_at. created_at is sufficient.
    """
    __tablename__ = "invitations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invited_by: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # The 6-digit code the child enters to join
    invite_code: Mapped[str] = mapped_column(
        String(6), nullable=False, unique=True, index=True
    )

    # Optional: parent can name who they're inviting
    invitee_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Lifecycle
    status: Mapped[InvitationStatus] = mapped_column(
        Enum(InvitationStatus, name="invitationstatus", create_type=True),
        nullable=False,
        default=InvitationStatus.SENT,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Set when a child actually joins
    accepted_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    family: Mapped["Family"] = relationship(  # noqa: F821
        "Family",
        back_populates="invitations",
        lazy="noload",
    )
    sender: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[invited_by],
        lazy="noload",
    )
    acceptor: Mapped["User | None"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[accepted_by],
        lazy="noload",
    )

    # ------------------------------------------------------------------ #
    # Indexes
    # ------------------------------------------------------------------ #
    __table_args__ = (
        # Fast query: all invitations for a family filtered by status
        Index("ix_invitations_family_status", "family_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Invitation id={self.id} code={self.invite_code} status={self.status}>"
