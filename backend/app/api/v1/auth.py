"""
Auth endpoints.

POST /api/v1/auth/register  — Register new user
POST /api/v1/auth/login     — Login → token pair
POST /api/v1/auth/refresh   — Rotate refresh token
POST /api/v1/auth/logout    — Revoke refresh token
POST /api/v1/auth/change-password — Change password (authenticated)
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.database import get_db
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.common import SuccessResponse
from app.schemas.user import UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register akun baru",
)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await auth_service.register(body, db)
    return SuccessResponse(data=UserResponse.model_validate(user))


@router.post(
    "/login",
    response_model=SuccessResponse[TokenResponse],
    summary="Login dan dapatkan token",
)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    device_info = request.headers.get("User-Agent")
    tokens = await auth_service.login(body, db, device_info=device_info)
    return SuccessResponse(data=tokens)


@router.post(
    "/refresh",
    response_model=SuccessResponse[TokenResponse],
    summary="Perbarui access token menggunakan refresh token",
)
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    tokens = await auth_service.refresh_tokens(body.refresh_token, db)
    return SuccessResponse(data=tokens)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout dan cabut refresh token",
)
async def logout(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),  # must be authenticated
):
    await auth_service.logout(body.refresh_token, db)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Ganti password (membutuhkan login)",
)
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    await auth_service.change_password(current_user, body, db)
