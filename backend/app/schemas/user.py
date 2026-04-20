"""
User-related Pydantic v2 schemas.
"""

import uuid
from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, EmailStr, Field

from app.core.constants import UserRole


class UserResponse(BaseModel):
    """Safe user representation — never includes hashed_password."""
    id: uuid.UUID
    email: EmailStr
    full_name: str
    avatar_url: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdateUserRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    avatar_url: AnyHttpUrl | None = Field(default=None)
