"""
Family & Invitation Pydantic v2 schemas.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.constants import FamilyMemberRole, InvitationStatus


# ------------------------------------------------------------------ #
# Family schemas
# ------------------------------------------------------------------ #

class CreateFamilyRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class FamilyResponse(BaseModel):
    id: uuid.UUID
    name: str
    created_by: uuid.UUID
    max_seats: int
    created_at: datetime

    model_config = {"from_attributes": True}


class FamilyMemberResponse(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    user_id: uuid.UUID
    full_name: str        # denormalized from user
    email: str            # denormalized from user
    role: FamilyMemberRole
    is_active: bool
    joined_at: datetime

    model_config = {"from_attributes": True}


class FamilyDetailResponse(BaseModel):
    """Family with member list — used for GET /families/me."""
    id: uuid.UUID
    name: str
    created_by: uuid.UUID
    max_seats: int
    member_count: int
    members: list[FamilyMemberResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------ #
# Invitation schemas
# ------------------------------------------------------------------ #

class CreateInvitationRequest(BaseModel):
    invitee_name: str | None = Field(default=None, max_length=100)


class JoinFamilyRequest(BaseModel):
    invite_code: str = Field(min_length=6, max_length=6)

    @field_validator("invite_code")
    @classmethod
    def code_must_be_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Kode undangan harus berupa 6 digit angka.")
        return v


class InvitationResponse(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    invite_code: str
    invitee_name: str | None
    status: InvitationStatus
    expires_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
