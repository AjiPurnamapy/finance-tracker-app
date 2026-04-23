"""
Notification service — create, list, read, mark-all-read.
"""

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from typing import Optional, Any, List

from app.models.notification import Notification
from app.core.constants import NotificationType
from app.core.exceptions import NotFoundException

log = structlog.get_logger(__name__)


async def create_notification(
    session: AsyncSession,
    user_id: uuid.UUID,
    type: NotificationType,
    title: str,
    message: str,
    data: Optional[Any] = None
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        data=data
    )
    session.add(notification)
    await session.flush()
    await session.refresh(notification)

    log.info(
        "notification_created",
        notification_id=str(notification.id),
        user_id=str(user_id),
        type=type.value,
    )
    return notification


async def list_notifications(
    session: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20
) -> tuple[List[Notification], int]:
    offset = (page - 1) * per_page

    # Get total count
    count_query = select(func.count()).select_from(Notification).where(Notification.user_id == user_id)
    total = await session.scalar(count_query)

    # Get items
    query = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await session.execute(query)
    items = result.scalars().all()

    return list(items), total


async def get_unread_count(session: AsyncSession, user_id: uuid.UUID) -> int:
    query = select(func.count()).select_from(Notification).where(
        Notification.user_id == user_id,
        Notification.is_read == False  # noqa: E712
    )
    return await session.scalar(query)


async def mark_read(session: AsyncSession, user_id: uuid.UUID, notification_id: uuid.UUID) -> Notification:
    query = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id
    )
    result = await session.execute(query)
    notification = result.scalar_one_or_none()

    if not notification:
        raise NotFoundException(code="NOTIFICATION_NOT_FOUND", message="Notification not found")

    notification.is_read = True
    await session.flush()
    await session.refresh(notification)

    log.info("notification_read", notification_id=str(notification_id), user_id=str(user_id))
    return notification


async def mark_all_read(session: AsyncSession, user_id: uuid.UUID) -> int:
    stmt = update(Notification).where(
        Notification.user_id == user_id,
        Notification.is_read == False  # noqa: E712
    ).values(is_read=True)

    result = await session.execute(stmt)
    await session.flush()

    log.info("notifications_mark_all_read", user_id=str(user_id), count=result.rowcount)
    return result.rowcount
