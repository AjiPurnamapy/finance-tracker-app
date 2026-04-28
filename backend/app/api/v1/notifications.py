import math
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.notification import (
    NotificationResponse,
    NotificationPaginationMeta,
    PaginatedNotificationResponse,
)
from app.services import notification_service

router = APIRouter()


@router.get("", response_model=PaginatedNotificationResponse)
async def list_notifications(
    page: int = Query(1, ge=1, description="Nomor halaman"),
    per_page: int = Query(20, ge=1, le=100, description="Jumlah item per halaman"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    items, total = await notification_service.list_notifications(
        db, current_user.id, page=page, per_page=per_page
    )
    total_pages = math.ceil(total / per_page) if total > 0 else 0
    return PaginatedNotificationResponse(
        data=[NotificationResponse.model_validate(n) for n in items],
        meta=NotificationPaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
        ),
    )


@router.get("/unread-count", response_model=dict)
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    count = await notification_service.get_unread_count(db, current_user.id)
    return {"unread_count": count}


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.mark_read(db, current_user.id, notification_id)


@router.post("/read-all", status_code=200)
async def mark_all_as_read(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await notification_service.mark_all_read(db, current_user.id)
    return {"status": "ok"}
