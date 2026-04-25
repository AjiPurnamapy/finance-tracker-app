"""
Task service — task lifecycle with state machine enforcement.

State machine:
  created   → submitted  (child only)
  created   → [deleted]  (parent only, while still created)
  submitted → approved   (parent only → reward paid → completed)
  submitted → rejected   (parent only)

Any other transition raises InvalidStateTransitionException.
"""

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    FamilyMemberRole,
    TaskStatus,
    TransactionType,
    NotificationType,
)
from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    InvalidStateTransitionException,
    NotFoundException,
)
from app.models.family import FamilyMember
from app.models.task import Task
from app.models.user import User
from app.schemas.task import CreateTaskRequest, TaskResponse, UpdateTaskRequest
from app.services import transaction_service, wallet_service, notification_service

log = structlog.get_logger(__name__)

# Valid status transitions
_VALID_TRANSITIONS: dict[TaskStatus, list[TaskStatus]] = {
    TaskStatus.CREATED: [TaskStatus.SUBMITTED],       # child submits
    TaskStatus.SUBMITTED: [TaskStatus.APPROVED, TaskStatus.REJECTED],
    TaskStatus.APPROVED: [TaskStatus.COMPLETED],      # auto after reward
    TaskStatus.REJECTED: [],                          # terminal
    TaskStatus.COMPLETED: [],                         # terminal
}


def _assert_valid_transition(current: TaskStatus, target: TaskStatus) -> None:
    if target not in _VALID_TRANSITIONS.get(current, []):
        raise InvalidStateTransitionException(
            current=current.value, target=target.value
        )


async def _get_user_family_membership(
    user_id: uuid.UUID, db: AsyncSession
) -> FamilyMember:
    """Get active membership or raise 403."""
    membership = await db.scalar(
        select(FamilyMember).where(
            FamilyMember.user_id == user_id,
            FamilyMember.is_active == True,  # noqa: E712
        )
    )
    if not membership:
        raise ForbiddenException(
            code="NOT_IN_FAMILY",
            message="Anda belum tergabung dalam family.",
        )
    return membership


async def _get_task_with_family_check(
    task_id: uuid.UUID,
    user_family_id: uuid.UUID,
    db: AsyncSession,
) -> Task:
    """Get task and verify it belongs to user's family."""
    task = await db.get(Task, task_id)
    if not task:
        raise NotFoundException(resource="Task")
    if task.family_id != user_family_id:
        raise ForbiddenException(
            code="NOT_FAMILY_MEMBER",
            message="Anda tidak memiliki akses ke task ini.",
        )
    return task


# ------------------------------------------------------------------ #
# Public API
# ------------------------------------------------------------------ #

async def create_task(
    user: User,
    data: CreateTaskRequest,
    db: AsyncSession,
) -> TaskResponse:
    """
    Parent creates a task for a child.
    - Requester must be parent + family admin
    - assigned_to must be an active member of the same family
    - due_date (if given) must be in the future
    """
    if user.role != "parent":
        raise ForbiddenException(
            code="PARENT_ROLE_REQUIRED",
            message="Hanya parent yang bisa membuat task.",
        )

    # Verify parent is admin of their family
    membership = await db.scalar(
        select(FamilyMember).where(
            FamilyMember.user_id == user.id,
            FamilyMember.is_active == True,  # noqa: E712
            FamilyMember.role == FamilyMemberRole.ADMIN,
        )
    )
    if not membership:
        raise ForbiddenException(
            code="NOT_IN_FAMILY",
            message="Anda belum tergabung dalam family.",
        )

    # Verify assigned_to is an active member of the same family
    assignee_membership = await db.scalar(
        select(FamilyMember).where(
            FamilyMember.family_id == membership.family_id,
            FamilyMember.user_id == data.assigned_to,
            FamilyMember.is_active == True,  # noqa: E712
        )
    )
    if not assignee_membership:
        raise ForbiddenException(
            code="ASSIGNEE_NOT_IN_FAMILY",
            message="Anak yang dipilih bukan anggota family ini.",
        )

    # Prevent assigning task to self (parent cannot assign to parent)
    if data.assigned_to == user.id:
        raise ForbiddenException(
            code="CANNOT_ASSIGN_TO_SELF",
            message="Parent tidak bisa membuat task untuk diri sendiri.",
        )

    # Validate due_date is in future
    if data.due_date and data.due_date.replace(tzinfo=None) <= datetime.now(UTC).replace(tzinfo=None):
        raise BadRequestException(
            code="DUE_DATE_IN_PAST",
            message="Due date harus di masa mendatang.",
        )

    task = Task(
        family_id=membership.family_id,
        created_by=user.id,
        assigned_to=data.assigned_to,
        title=data.title.strip(),
        description=data.description,
        reward_amount=data.reward_amount,
        reward_currency=data.reward_currency,
        status=TaskStatus.CREATED,
        due_date=data.due_date,
        is_recurring=data.is_recurring,
        recurrence_type=data.recurrence_type,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    # G-1: Notify child that a new task has been assigned to them
    await notification_service.create_notification(
        session=db,
        user_id=task.assigned_to,
        type=NotificationType.TASK_ASSIGNED,
        title="Task Baru Untukmu!",
        message=f"Parent membuat task baru: '{task.title}'. "
                f"Reward: {task.reward_amount} {task.reward_currency.value}.",
        data={"task_id": str(task.id)},
    )

    log.info(
        "task_created",
        task_id=str(task.id),
        family_id=str(membership.family_id),
        assigned_to=str(data.assigned_to),
    )
    return TaskResponse.model_validate(task)


async def list_tasks(
    user: User,
    db: AsyncSession,
    status_filter: TaskStatus | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[TaskResponse], int]:
    """
    Parent: all tasks in their family (optionally filtered by status).
    Child: only tasks assigned to themselves.
    Returns (tasks, total_count) untuk pagination.
    """
    membership = await _get_user_family_membership(user.id, db)

    base_query = select(Task).where(Task.family_id == membership.family_id)

    if user.role == "child":
        base_query = base_query.where(Task.assigned_to == user.id)

    if status_filter:
        base_query = base_query.where(Task.status == status_filter)

    # Count total
    total = await db.scalar(
        select(func.count()).select_from(base_query.subquery())
    ) or 0

    # Paginate
    offset = (page - 1) * per_page
    result = await db.execute(
        base_query.order_by(Task.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    tasks = result.scalars().all()
    return [TaskResponse.model_validate(t) for t in tasks], total


async def get_task(
    task_id: uuid.UUID,
    user: User,
    db: AsyncSession,
) -> TaskResponse:
    """Get a single task. User must be in the same family."""
    membership = await _get_user_family_membership(user.id, db)
    task = await _get_task_with_family_check(task_id, membership.family_id, db)

    # Child can only see tasks assigned to them
    if user.role == "child" and task.assigned_to != user.id:
        raise ForbiddenException(
            code="NOT_YOUR_TASK",
            message="Anda tidak memiliki akses ke task ini.",
        )

    return TaskResponse.model_validate(task)


async def update_task(
    task_id: uuid.UUID,
    user: User,
    data: UpdateTaskRequest,
    db: AsyncSession,
) -> TaskResponse:
    """
    Parent can edit task details only while status=created.
    """
    if user.role != "parent":
        raise ForbiddenException(
            code="PARENT_ROLE_REQUIRED",
            message="Hanya parent yang bisa mengubah task.",
        )

    membership = await _get_user_family_membership(user.id, db)
    task = await _get_task_with_family_check(task_id, membership.family_id, db)

    if task.status != TaskStatus.CREATED:
        raise ForbiddenException(
            code="TASK_NOT_EDITABLE",
            message="Task hanya bisa diubah saat status=created.",
        )

    # Use model_fields_set to distinguish "not sent" vs "sent as null"
    fields_sent = data.model_fields_set

    if "title" in fields_sent and data.title is not None:
        task.title = data.title.strip()
    if "description" in fields_sent:
        task.description = data.description  # allows clearing to None
    if "reward_amount" in fields_sent and data.reward_amount is not None:
        task.reward_amount = data.reward_amount
    if "reward_currency" in fields_sent and data.reward_currency is not None:
        task.reward_currency = data.reward_currency
    if "due_date" in fields_sent:
        # F-10: Validate due_date is in the future (matching create_task behavior)
        if data.due_date and data.due_date.replace(tzinfo=None) <= datetime.now(UTC).replace(tzinfo=None):
            raise BadRequestException(
                code="DUE_DATE_IN_PAST",
                message="Due date harus di masa mendatang.",
            )
        task.due_date = data.due_date  # allows clearing to None

    db.add(task)
    await db.flush()
    await db.refresh(task)
    return TaskResponse.model_validate(task)


async def delete_task(
    task_id: uuid.UUID,
    user: User,
    db: AsyncSession,
) -> None:
    """Parent can delete task only while status=created."""
    if user.role != "parent":
        raise ForbiddenException(
            code="PARENT_ROLE_REQUIRED",
            message="Hanya parent yang bisa menghapus task.",
        )

    membership = await _get_user_family_membership(user.id, db)
    task = await _get_task_with_family_check(task_id, membership.family_id, db)

    if task.status != TaskStatus.CREATED:
        raise ForbiddenException(
            code="TASK_NOT_DELETABLE",
            message="Task yang sudah disubmit tidak bisa dihapus.",
        )

    await db.delete(task)
    await db.flush()
    log.info("task_deleted", task_id=str(task_id), by=str(user.id))


async def submit_task(
    task_id: uuid.UUID,
    user: User,
    db: AsyncSession,
) -> TaskResponse:
    """Child marks task as submitted for parent review."""
    if user.role != "child":
        raise ForbiddenException(
            code="CHILD_ROLE_REQUIRED",
            message="Hanya anak yang bisa submit task.",
        )

    membership = await _get_user_family_membership(user.id, db)
    task = await _get_task_with_family_check(task_id, membership.family_id, db)

    # Only the assigned child can submit
    if task.assigned_to != user.id:
        raise ForbiddenException(
            code="NOT_YOUR_TASK",
            message="Anda tidak bisa submit task yang bukan milik Anda.",
        )

    _assert_valid_transition(task.status, TaskStatus.SUBMITTED)
    task.status = TaskStatus.SUBMITTED
    db.add(task)
    await db.flush()
    await db.refresh(task)

    # Notify parent
    await notification_service.create_notification(
        session=db,
        user_id=task.created_by,
        type=NotificationType.TASK_SUBMITTED,
        title="Task Disubmit",
        message=f"Anak telah men-submit task: {task.title}",
        data={"task_id": str(task.id)}
    )

    log.info("task_submitted", task_id=str(task_id), by=str(user.id))
    return TaskResponse.model_validate(task)


async def approve_task(
    task_id: uuid.UUID,
    user: User,
    db: AsyncSession,
) -> TaskResponse:
    """
    Parent approves submitted task:
    1. Transition: submitted → approved → completed
    2. Credit child wallet with reward
    3. Create immutable transaction record

    IMPORTANT: All operations (credit, create_tx, update task) run within
    a single DB transaction from get_db(). If any step fails, the entire
    transaction is rolled back — ensuring financial atomicity.
    """
    if user.role != "parent":
        raise ForbiddenException(
            code="PARENT_ROLE_REQUIRED",
            message="Hanya parent yang bisa approve task.",
        )

    membership = await _get_user_family_membership(user.id, db)
    task = await _get_task_with_family_check(task_id, membership.family_id, db)

    _assert_valid_transition(task.status, TaskStatus.APPROVED)

    # Get child's wallet
    child_wallet = await wallet_service.get_wallet_by_user_id(task.assigned_to, db)

    # Credit child wallet
    # NOTE: child_wallet object becomes stale after credit() because
    # credit() uses a raw UPDATE statement. Do NOT read balance from
    # this object after credit — use a fresh query if needed.
    await wallet_service.credit(
        wallet_id=child_wallet.id,
        amount=task.reward_amount,
        currency=task.reward_currency,
        db=db,
    )

    # Create immutable transaction record
    tx = await transaction_service.create_transaction(
        family_id=task.family_id,
        source_wallet_id=None,          # reward comes from "system" / parent budget
        destination_wallet_id=child_wallet.id,
        amount=task.reward_amount,
        currency=task.reward_currency,
        type=TransactionType.TASK_REWARD,
        description=f"Reward task: {task.title}",
        reference_type="task",
        reference_id=task.id,
        db=db,
    )

    # Mark task as completed (approved + reward paid = completed)
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.now(UTC)
    task.reward_transaction_id = tx.id
    db.add(task)
    await db.flush()
    await db.refresh(task)

    # Notify child
    await notification_service.create_notification(
        session=db,
        user_id=task.assigned_to,
        type=NotificationType.TASK_APPROVED,
        title="Task Disetujui!",
        message=f"Task '{task.title}' disetujui. Kamu mendapatkan {task.reward_amount} {task.reward_currency}!",
        data={"task_id": str(task.id)}
    )

    log.info(
        "task_approved",
        task_id=str(task_id),
        reward=str(task.reward_amount),
        currency=task.reward_currency,
        child_id=str(task.assigned_to),
    )
    return TaskResponse.model_validate(task)


async def reject_task(
    task_id: uuid.UUID,
    user: User,
    db: AsyncSession,
) -> TaskResponse:
    """Parent rejects submitted task. No wallet changes."""
    if user.role != "parent":
        raise ForbiddenException(
            code="PARENT_ROLE_REQUIRED",
            message="Hanya parent yang bisa reject task.",
        )

    membership = await _get_user_family_membership(user.id, db)
    task = await _get_task_with_family_check(task_id, membership.family_id, db)

    _assert_valid_transition(task.status, TaskStatus.REJECTED)
    task.status = TaskStatus.REJECTED
    db.add(task)
    await db.flush()
    await db.refresh(task)

    # Notify child
    await notification_service.create_notification(
        session=db,
        user_id=task.assigned_to,
        type=NotificationType.TASK_REJECTED,
        title="Task Ditolak",
        message=f"Task '{task.title}' ditolak oleh parent.",
        data={"task_id": str(task.id)}
    )

    log.info("task_rejected", task_id=str(task_id), by=str(user.id))
    return TaskResponse.model_validate(task)
