"""
Family endpoints.

POST   /api/v1/families/        — Create family (parent only)
GET    /api/v1/families/me      — Get my family + members
GET    /api/v1/families/{id}/members       — List family members
DELETE /api/v1/families/{id}/members/{uid} — Remove member (admin only)
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, require_parent
from app.database import get_db
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.family import (
    CreateFamilyRequest,
    FamilyDetailResponse,
    FamilyMemberResponse,
    FamilyResponse,
)
from app.services import family_service

router = APIRouter(prefix="/families", tags=["Families"])


@router.post(
    "/",
    response_model=SuccessResponse[FamilyResponse],
    status_code=201,
    summary="Buat family baru",
)
async def create_family(
    body: CreateFamilyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_parent),
):
    family = await family_service.create_family(current_user, body, db)
    return SuccessResponse(data=family)


@router.get(
    "/me",
    response_model=SuccessResponse[FamilyDetailResponse],
    summary="Lihat family saya beserta anggota",
)
async def get_my_family(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    family = await family_service.get_user_family(current_user, db)
    return SuccessResponse(data=family)


@router.get(
    "/{family_id}/members",
    response_model=SuccessResponse[list[FamilyMemberResponse]],
    summary="Lihat daftar anggota family",
)
async def get_family_members(
    family_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    members = await family_service.get_members(family_id, current_user, db)
    return SuccessResponse(data=members)


@router.delete(
    "/{family_id}/members/{target_user_id}",
    status_code=204,
    summary="Hapus anggota dari family (admin only)",
)
async def remove_family_member(
    family_id: uuid.UUID,
    target_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_parent),
):
    await family_service.remove_member(family_id, target_user_id, current_user, db)
