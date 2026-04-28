"""
User profile endpoints.

GET   /api/v1/users/me  — Get own profile
PATCH /api/v1/users/me  — Update name / avatar
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.user import UpdateUserRequest, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=SuccessResponse[UserResponse],
    summary="Lihat profil saya",
)
async def get_me(
    current_user: User = Depends(get_current_active_user),
):
    return SuccessResponse(data=UserResponse.model_validate(current_user))


@router.patch(
    "/me",
    response_model=SuccessResponse[UserResponse],
    summary="Perbarui profil saya",
)
async def update_me(
    body: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if body.full_name is not None:
        current_user.full_name = body.full_name.strip()
    if body.avatar_url is not None:
        current_user.avatar_url = str(body.avatar_url)
    # NOTE: role update is intentionally not handled here.
    # Self-service role change would be a privilege escalation vulnerability.

    db.add(current_user)
    await db.flush()
    return SuccessResponse(data=UserResponse.model_validate(current_user))
