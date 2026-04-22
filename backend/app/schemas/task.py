"""
Task & Wallet Pydantic v2 schemas.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.core.constants import Currency, RecurrenceType, TaskStatus, TransactionType


# ------------------------------------------------------------------ #
# Wallet schemas
# ------------------------------------------------------------------ #

class WalletResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    balance_idr: Decimal
    balance_pts: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------ #
# Task schemas
# ------------------------------------------------------------------ #

class CreateTaskRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    assigned_to: uuid.UUID                         # must be child in same family
    reward_amount: Decimal = Field(gt=0, le=Decimal("99999999.99"), decimal_places=2)
    reward_currency: Currency = Currency.IDR
    due_date: datetime | None = None
    is_recurring: bool = False
    recurrence_type: RecurrenceType | None = None

    @field_validator("reward_amount")
    @classmethod
    def reward_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Reward amount harus lebih dari 0.")
        return v

    @field_validator("recurrence_type")
    @classmethod
    def recurrence_required_if_recurring(
        cls, v: RecurrenceType | None, info
    ) -> RecurrenceType | None:
        if info.data.get("is_recurring") and v is None:
            raise ValueError(
                "recurrence_type wajib diisi jika is_recurring=True."
            )
        return v


class UpdateTaskRequest(BaseModel):
    """Only editable while status=created."""
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    reward_amount: Decimal | None = Field(default=None, gt=0, le=Decimal("99999999.99"), decimal_places=2)
    reward_currency: Currency | None = None
    due_date: datetime | None = None


class TaskResponse(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    created_by: uuid.UUID
    assigned_to: uuid.UUID
    title: str
    description: str | None
    reward_amount: Decimal
    reward_currency: Currency
    status: TaskStatus
    due_date: datetime | None
    is_recurring: bool
    recurrence_type: RecurrenceType | None
    completed_at: datetime | None
    reward_transaction_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------ #
# Transaction schemas
# ------------------------------------------------------------------ #

class TransactionResponse(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    source_wallet_id: uuid.UUID | None
    destination_wallet_id: uuid.UUID | None
    amount: Decimal
    currency: Currency
    type: TransactionType
    description: str
    reference_type: str | None
    reference_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
