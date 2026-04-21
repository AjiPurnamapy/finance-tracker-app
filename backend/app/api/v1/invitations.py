"""
Invitation endpoints.

POST   /api/v1/invitations/        — Create invitation (parent only)
POST   /api/v1/invitations/join    — Join family via invite code (child)
GET    /api/v1/invitations/family  — List my family's invitations (parent)
DELETE /api/v1/invitations/{id}    — Cancel invitation (parent/creator)
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, require_child, require_parent
from app.database import get_db
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.family import (
    CreateInvitationRequest,
    FamilyDetailResponse,
    InvitationResponse,
    JoinFamilyRequest,
)
from app.services import invitation_service

router = APIRouter(prefix="/invitations", tags=["Invitations"])


@router.post(
    "/",
    response_model=SuccessResponse[InvitationResponse],
    status_code=201,
    summary="Buat kode undangan baru",
)
async def create_invitation(
    body: CreateInvitationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_parent),
):
    invitation = await invitation_service.create_invitation(current_user, body, db)
    return SuccessResponse(data=invitation)


@router.post(
    "/join",
    response_model=SuccessResponse[FamilyDetailResponse],
    summary="Bergabung ke family via kode undangan",
)
async def join_family(
    body: JoinFamilyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_child),
):
    result = await invitation_service.join_family(current_user, body.invite_code, db)
    return SuccessResponse(data=result)


@router.get(
    "/family",
    response_model=SuccessResponse[list[InvitationResponse]],
    summary="Lihat semua undangan family saya",
)
async def list_invitations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_parent),
):
    invitations = await invitation_service.list_family_invitations(current_user, db)
    return SuccessResponse(data=invitations)


@router.delete(
    "/{invitation_id}",
    status_code=204,
    summary="Batalkan undangan",
)
async def cancel_invitation(
    invitation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_parent),
):
    await invitation_service.cancel_invitation(invitation_id, current_user, db)
