"""
FastAPI dependencies — injectable guards for route protection.
All auth-required routes use these as Depends() parameters.
"""

import uuid

import structlog
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User

log = structlog.get_logger(__name__)

# Bearer token extractor (reads Authorization: Bearer <token>)
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract and validate JWT from Authorization header.
    Returns the authenticated User object.
    Raises 401 if token is missing, invalid, or expired.
    """
    if not credentials:
        raise UnauthorizedException(
            code="NOT_AUTHENTICATED",
            message="Autentikasi diperlukan. Sertakan token Bearer.",
        )

    try:
        payload = decode_access_token(credentials.credentials)
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise ValueError("Missing sub claim")
        user_uuid = uuid.UUID(user_id_str)  # must be UUID object, not str
    except (JWTError, ValueError):
        raise UnauthorizedException(
            code="INVALID_TOKEN",
            message="Token tidak valid atau sudah kadaluarsa. Silakan login kembali.",
        )

    user = await db.get(User, user_uuid)
    if not user:
        raise UnauthorizedException(
            code="USER_NOT_FOUND",
            message="Pengguna tidak ditemukan.",
        )

    # Bind user context to structlog for all subsequent log calls
    structlog.contextvars.bind_contextvars(
        user_id=str(user.id), role=user.role
    )

    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """Extends get_current_user — also checks that account is active."""
    if not user.is_active:
        raise ForbiddenException(
            code="ACCOUNT_INACTIVE",
            message="Akun Anda telah dinonaktifkan. Hubungi administrator.",
        )
    return user


async def require_parent(
    user: User = Depends(get_current_active_user),
) -> User:
    """Only allows users with role=parent. Returns the user."""
    if user.role != "parent":
        raise ForbiddenException(
            code="PARENT_ROLE_REQUIRED",
            message="Fitur ini hanya tersedia untuk orang tua.",
        )
    return user


async def require_child(
    user: User = Depends(get_current_active_user),
) -> User:
    """Only allows users with role=child. Returns the user."""
    if user.role != "child":
        raise ForbiddenException(
            code="CHILD_ROLE_REQUIRED",
            message="Fitur ini hanya tersedia untuk anak.",
        )
    return user
