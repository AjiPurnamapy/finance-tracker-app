"""
Schemas untuk FundRequest — request/response untuk endpoint fund request.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field

from app.core.constants import Currency, FundRequestStatus, FundRequestType


class ReviewAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"


class CreateFundRequestRequest(BaseModel):
    amount: Decimal = Field(gt=0, le=Decimal("99999999.99"), decimal_places=2)
    currency: Currency = Currency.IDR
    type: FundRequestType = FundRequestType.ONE_TIME
    reason: str | None = Field(default=None, max_length=500)


class ReviewFundRequestRequest(BaseModel):
    action: ReviewAction
    note: str | None = Field(default=None, max_length=500)


class FundRequestResponse(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    child_id: uuid.UUID
    parent_id: uuid.UUID | None
    amount: Decimal
    currency: Currency
    type: FundRequestType
    reason: str | None
    status: FundRequestStatus
    reviewed_at: datetime | None
    transaction_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
