"""
Auth-related Pydantic v2 schemas.
Strict validation for registration, login, and token operations.
"""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.constants import UserRole


# ------------------------------------------------------------------ #
# Request schemas
# ------------------------------------------------------------------ #

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=100)
    role: UserRole

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Password must contain at least one uppercase letter and one digit."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password harus mengandung minimal satu huruf kapital.")
        if not re.search(r"\d", v):
            raise ValueError("Password harus mengandung minimal satu angka.")
        return v

    @field_validator("full_name")
    @classmethod
    def full_name_no_digits(cls, v: str) -> str:
        return v.strip()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def new_password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password baru harus mengandung minimal satu huruf kapital.")
        if not re.search(r"\d", v):
            raise ValueError("Password baru harus mengandung minimal satu angka.")
        return v


# ------------------------------------------------------------------ #
# Response schemas
# ------------------------------------------------------------------ #

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expiry
