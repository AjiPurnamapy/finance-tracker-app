"""
Task endpoints.

POST   /api/v1/tasks/              — Create task (parent only)
GET    /api/v1/tasks/              — List tasks (parent: all family, child: own)
GET    /api/v1/tasks/{id}          — Get task detail
PATCH  /api/v1/tasks/{id}          — Update task (parent, status=created only)
DELETE /api/v1/tasks/{id}          — Delete task (parent, status=created only)
POST   /api/v1/tasks/{id}/submit   — Child submits task
POST   /api/v1/tasks/{id}/approve  — Parent approves → reward paid
POST   /api/v1/tasks/{id}/reject   — Parent rejects
"""

import uuid
import math

from app.schemas.common import PaginatedResponse, PaginationMeta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, require_child, require_parent
from app.core.constants import TaskStatus
from app.database import get_db
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.task import CreateTaskRequest, TaskResponse, UpdateTaskRequest
from app.services import task_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post(
    "/",
    response_model=SuccessResponse[TaskResponse],
    status_code=201,
    summary="Buat task baru untuk anak",
)
async def create_task(
    body: CreateTaskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_parent),
):
    task = await task_service.create_task(current_user, body, db)
    return SuccessResponse(data=task)



@router.get(
    "/",
    response_model=PaginatedResponse[TaskResponse],
    summary="Lihat daftar task",
)
async def list_tasks(
    status: TaskStatus | None = Query(default=None, description="Filter by status"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    tasks, total = await task_service.list_tasks(
        current_user, db, status_filter=status, page=page, per_page=per_page
    )
    return PaginatedResponse(
        data=tasks,
        meta=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=math.ceil(total / per_page) if total else 0,
        ),
    )


@router.get(
    "/{task_id}",
    response_model=SuccessResponse[TaskResponse],
    summary="Lihat detail task",
)
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    task = await task_service.get_task(task_id, current_user, db)
    return SuccessResponse(data=task)


@router.patch(
    "/{task_id}",
    response_model=SuccessResponse[TaskResponse],
    summary="Update task (hanya saat status=created)",
)
async def update_task(
    task_id: uuid.UUID,
    body: UpdateTaskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_parent),
):
    task = await task_service.update_task(task_id, current_user, body, db)
    return SuccessResponse(data=task)


@router.delete(
    "/{task_id}",
    status_code=204,
    summary="Hapus task (hanya saat status=created)",
)
async def delete_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_parent),
):
    await task_service.delete_task(task_id, current_user, db)


@router.post(
    "/{task_id}/submit",
    response_model=SuccessResponse[TaskResponse],
    summary="Anak submit task untuk direview",
)
async def submit_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_child),
):
    task = await task_service.submit_task(task_id, current_user, db)
    return SuccessResponse(data=task)


@router.post(
    "/{task_id}/approve",
    response_model=SuccessResponse[TaskResponse],
    summary="Parent approve task → reward otomatis masuk wallet anak",
)
async def approve_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_parent),
):
    task = await task_service.approve_task(task_id, current_user, db)
    return SuccessResponse(data=task)


@router.post(
    "/{task_id}/reject",
    response_model=SuccessResponse[TaskResponse],
    summary="Parent reject task",
)
async def reject_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_parent),
):
    task = await task_service.reject_task(task_id, current_user, db)
    return SuccessResponse(data=task)
