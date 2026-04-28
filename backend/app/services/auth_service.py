"""
Auth service — all authentication business logic.

Security practices applied:
- Generic error messages: login never reveals whether email exists
- Refresh token rotation: old token revoked on every refresh
- Tokens stored as SHA-256 hash, plain token only returned to client once
"""

import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import (
    EmailAlreadyExistsException,
    UnauthorizedException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)

log = structlog.get_logger(__name__)

# CVE-3 FIX: Pre-compute dummy Argon2 hash at module load time.
# Previously, hash_password("dummy") was called on every failed login,
# creating a new Argon2 hash each time. This introduced a subtle timing
# difference vs. verifying an existing hash, which a sophisticated
# attacker could exploit for user enumeration.
_TIMING_DUMMY_HASH = hash_password("__timing_attack_protection_dummy__")


def _build_token_response(
    user: User,
    plain_refresh_token: str,
) -> TokenResponse:
    settings = get_settings()
    access_token = create_access_token(
        sub=str(user.id),
        role=user.role,
        # family_id: intentionally None — JWT tidak menyimpan family context
        # untuk menghindari stale token issue saat user berpindah family.
        # Family context selalu di-fetch fresh dari DB per request.
        family_id=None,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=plain_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def register(
    data: RegisterRequest,
    db: AsyncSession,
) -> User:
    """
    Register a new user.
    - Checks for duplicate email (case-insensitive)
    - Hashes password with Argon2id + pepper
    - Creates user
    
    NOTE: Wallet is auto-created for every new user (Phase 4).
    """
    # 1. Check for duplicate email
    existing = await db.scalar(
        select(User).where(User.email == data.email.lower())
    )
    if existing:
        raise EmailAlreadyExistsException()

    # 2. Create user
    user = User(
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        full_name=data.full_name.strip(),
        role=data.role,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.flush()  # get the UUID assigned without committing yet

    # 3. Auto-create wallet for every new user (Phase 4)
    wallet = Wallet(user_id=user.id)
    db.add(wallet)
    await db.flush()

    log.info("user_registered", user_id=str(user.id), role=user.role)
    return user


async def login(
    data: LoginRequest,
    db: AsyncSession,
    device_info: str | None = None,
) -> TokenResponse:
    """
    Authenticate user and return token pair.
    Uses generic error for wrong email OR wrong password (no info leak).
    """
    _invalid = UnauthorizedException(
        code="INVALID_CREDENTIALS",
        message="Email atau password salah.",
    )

    # 1. Find user (case-insensitive email)
    user = await db.scalar(
        select(User).where(User.email == data.email.lower())
    )
    if not user:
        # CVE-3 FIX: Use pre-computed hash to eliminate timing side-channel.
        # verify_password always runs against a real Argon2 hash, matching
        # the timing of a genuine "wrong password" verification.
        verify_password("__timing_attack_protection_dummy__", _TIMING_DUMMY_HASH)
        log.warning("login_failed_user_not_found", email=data.email)
        raise _invalid

    # 2. Verify password
    if not verify_password(data.password, user.hashed_password):
        log.warning("login_failed_wrong_password", user_id=str(user.id))
        raise _invalid

    # 3. Check account active
    if not user.is_active:
        raise UnauthorizedException(
            code="ACCOUNT_INACTIVE",
            message="Akun Anda telah dinonaktifkan. Hubungi administrator.",
        )

    # S-2 FIX: Cleanup expired/revoked tokens to prevent table bloat
    await db.execute(
        delete(RefreshToken).where(
            RefreshToken.user_id == user.id,
            or_(
                RefreshToken.is_revoked == True,  # noqa: E712
                RefreshToken.expires_at < datetime.now(UTC),
            ),
        )
    )

    # 4. Create and store refresh token
    plain_token = create_refresh_token()
    settings = get_settings()
    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(plain_token),
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        is_revoked=False,
        device_info=device_info,
        created_at=datetime.now(UTC),
    )
    db.add(refresh_token)
    await db.flush()

    log.info("user_logged_in", user_id=str(user.id))
    return _build_token_response(user, plain_token)


async def refresh_tokens(
    plain_refresh_token: str,
    db: AsyncSession,
) -> TokenResponse:
    """
    Rotate refresh tokens.
    - Validates plain token matches a non-revoked, non-expired DB record
    - Revokes old token
    - Issues new token pair
    """
    token_hash = hash_token(plain_refresh_token)

    # 1. Find matching token record
    record = await db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False,  # noqa: E712
        )
    )
    if not record:
        raise UnauthorizedException(
            code="INVALID_REFRESH_TOKEN",
            message="Refresh token tidak valid atau sudah tidak aktif.",
        )

    # 2. Check expiry — SQLite strips tzinfo on read, normalize before compare
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        raise UnauthorizedException(
            code="REFRESH_TOKEN_EXPIRED",
            message="Sesi Anda telah berakhir. Silakan login kembali.",
        )

    # 3. Load user
    user = await db.get(User, record.user_id)
    if not user or not user.is_active:
        raise UnauthorizedException(
            code="ACCOUNT_INACTIVE",
            message="Akun tidak aktif.",
        )

    # 4. Revoke old token (rotation)
    record.is_revoked = True
    db.add(record)

    # 5. Issue new token
    plain_new = create_refresh_token()
    settings = get_settings()
    new_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(plain_new),
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        is_revoked=False,
        device_info=record.device_info,
        created_at=datetime.now(UTC),
    )
    db.add(new_record)
    await db.flush()

    log.info("tokens_refreshed", user_id=str(user.id))
    return _build_token_response(user, plain_new)


async def logout(
    plain_refresh_token: str,
    db: AsyncSession,
) -> None:
    """Revoke the provided refresh token."""
    token_hash = hash_token(plain_refresh_token)
    record = await db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
        )
    )
    if record:
        record.is_revoked = True
        db.add(record)
        await db.flush()  # make revocation visible within the same session
    # Silently succeed even if token not found (idempotent)
    log.info("user_logged_out")


async def change_password(
    user: User,
    data: ChangePasswordRequest,
    db: AsyncSession,
) -> None:
    """
    Change password for authenticated user.
    - Verifies current password first
    - Revokes all existing refresh tokens (force re-login on all devices)
    """
    if not verify_password(data.current_password, user.hashed_password):
        raise UnauthorizedException(
            code="WRONG_CURRENT_PASSWORD",
            message="Password saat ini salah.",
        )

    # Update password
    user.hashed_password = hash_password(data.new_password)
    db.add(user)

    # Revoke all refresh tokens (security: force re-login everywhere)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id)
        .values(is_revoked=True)
    )
    await db.flush()
    log.info("password_changed", user_id=str(user.id))
