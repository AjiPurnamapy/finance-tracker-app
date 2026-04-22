"""
Schemas untuk Allowance — request/response untuk endpoint allowance.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.constants import Currency, RecurrenceType


class CreateAllowanceRequest(BaseModel):
    child_id: uuid.UUID
    amount: Decimal = Field(gt=0, le=Decimal("99999999.99"), decimal_places=2)
    currency: Currency = Currency.IDR
    is_recurring: bool = True
    recurrence_type: RecurrenceType | None = None
    next_payment_at: datetime | None = None


class UpdateAllowanceRequest(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0, le=Decimal("99999999.99"), decimal_places=2)
    currency: Currency | None = None
    is_recurring: bool | None = None
    recurrence_type: RecurrenceType | None = None
    next_payment_at: datetime | None = None
    is_active: bool | None = None


class AllowanceResponse(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    parent_id: uuid.UUID
    child_id: uuid.UUID
    amount: Decimal
    currency: Currency
    is_recurring: bool
    recurrence_type: RecurrenceType | None
    next_payment_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
