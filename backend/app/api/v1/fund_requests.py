"""
FundRequest router — endpoints untuk sistem permintaan dana.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, require_child, require_parent
from app.core.constants import FundRequestStatus
from app.database import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse, PaginationMeta, SuccessResponse
from app.schemas.fund_request import CreateFundRequestRequest, FundRequestResponse
from app.services import fund_request_service

router = APIRouter(prefix="/fund-requests", tags=["Fund Requests"])


@router.post("/", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_fund_request(
    data: CreateFundRequestRequest,
    child: User = Depends(require_child),
    db: AsyncSession = Depends(get_db),
):
    result = await fund_request_service.create_request(child, data, db)
    return SuccessResponse(data=result)


@router.get("/", response_model=PaginatedResponse)
async def list_fund_requests(
    status: FundRequestStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    results, total = await fund_request_service.list_requests(
        user, db, status=status, page=page, per_page=per_page
    )
    import math
    return PaginatedResponse(
        data=results,
        meta=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=math.ceil(total / per_page) if total else 0,
        ),
    )


@router.get("/{request_id}", response_model=SuccessResponse)
async def get_fund_request(
    request_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await fund_request_service.get_request(request_id, user, db)
    return SuccessResponse(data=result)


@router.post("/{request_id}/approve", response_model=SuccessResponse)
async def approve_fund_request(
    request_id: uuid.UUID,
    parent: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    result = await fund_request_service.approve_request(request_id, parent, db)
    return SuccessResponse(data=result)


@router.post("/{request_id}/reject", response_model=SuccessResponse)
async def reject_fund_request(
    request_id: uuid.UUID,
    parent: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    result = await fund_request_service.reject_request(request_id, parent, db)
    return SuccessResponse(data=result)
