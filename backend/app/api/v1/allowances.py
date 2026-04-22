"""
Allowance router — endpoints untuk manajemen uang saku.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, require_parent
from app.database import get_db
from app.models.user import User
from app.schemas.allowance import AllowanceResponse, CreateAllowanceRequest, UpdateAllowanceRequest
from app.schemas.common import SuccessResponse
from app.schemas.task import TransactionResponse
from app.services import allowance_service

router = APIRouter(prefix="/allowances", tags=["Allowances"])


@router.post("/", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_allowance(
    data: CreateAllowanceRequest,
    parent: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    result = await allowance_service.create_allowance(parent, data, db)
    return SuccessResponse(data=result)


@router.get("/", response_model=SuccessResponse)
async def list_allowances(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    results = await allowance_service.list_allowances(user, db)
    return SuccessResponse(data=results)


@router.get("/{allowance_id}", response_model=SuccessResponse)
async def get_allowance(
    allowance_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await allowance_service.get_allowance(allowance_id, user, db)
    return SuccessResponse(data=result)


@router.patch("/{allowance_id}", response_model=SuccessResponse)
async def update_allowance(
    allowance_id: uuid.UUID,
    data: UpdateAllowanceRequest,
    parent: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    result = await allowance_service.update_allowance(allowance_id, parent, data, db)
    return SuccessResponse(data=result)


@router.post("/{allowance_id}/transfer", response_model=SuccessResponse)
async def manual_transfer(
    allowance_id: uuid.UUID,
    parent: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger allowance transfer from parent wallet to child wallet."""
    result = await allowance_service.manual_transfer(allowance_id, parent, db)
    return SuccessResponse(data=result)
