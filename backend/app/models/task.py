"""
Task model — tugas yang diberikan parent kepada child.

State machine:
  created → submitted  (child submits)
  created → [deleted]  (parent deletes, only while created)
  submitted → approved (parent approves → reward paid)
  submitted → rejected (parent rejects)
  approved  → completed (auto-set after reward credited)

Invalid transitions (blocked):
  submitted → created  (no undo)
  approved  → rejected (reward already paid)
  rejected  → approved (create new task instead)
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DECIMAL,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import Currency, RecurrenceType, TaskStatus
from app.models.base import BaseModel


class Task(BaseModel):
    __tablename__ = "tasks"

    # ------------------------------------------------------------------ #
    # Core identity
    # ------------------------------------------------------------------ #
    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assigned_to: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Task details
    # ------------------------------------------------------------------ #
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Reward configuration
    reward_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2), nullable=False
    )
    reward_currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency", create_type=False),  # shared with transactions
        nullable=False,
    )

    # ------------------------------------------------------------------ #
    # State machine
    # ------------------------------------------------------------------ #
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="taskstatus", create_type=True),
        nullable=False,
        default=TaskStatus.CREATED,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Scheduling
    # ------------------------------------------------------------------ #
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_recurring: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    recurrence_type: Mapped[RecurrenceType | None] = mapped_column(
        Enum(RecurrenceType, name="recurrencetype", create_type=True),
        nullable=True,
    )

    # ------------------------------------------------------------------ #
    # Completion tracking
    # ------------------------------------------------------------------ #
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Reference to the reward transaction (set after approve)
    reward_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    family: Mapped["Family"] = relationship(  # noqa: F821
        "Family",
        lazy="noload",
    )
    creator: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[created_by],
        lazy="noload",
    )
    assignee: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[assigned_to],
        lazy="noload",
    )

    # ------------------------------------------------------------------ #
    # Indexes
    # ------------------------------------------------------------------ #
    __table_args__ = (
        # Parent queries: all tasks in a family by status
        Index("ix_tasks_family_status", "family_id", "status"),
        # Child queries: tasks assigned to me by status
        Index("ix_tasks_assigned_status", "assigned_to", "status"),
    )

    def __repr__(self) -> str:
        return f"<Task id={self.id} title={self.title!r} status={self.status}>"
