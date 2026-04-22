"""
Schemas untuk Expense — request/response untuk endpoint expense.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.constants import Currency, ExpenseCategory, EXPENSE_CATEGORY_LABELS


class CreateExpenseRequest(BaseModel):
    amount: Decimal = Field(gt=0, le=Decimal("99999999.99"), decimal_places=2)
    currency: Currency = Currency.IDR  # MVP: IDR only
    category: ExpenseCategory
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    spent_at: datetime | None = None  # defaults to now() in service
    deduct_from_wallet: bool = False


class UpdateExpenseRequest(BaseModel):
    """Only non-financial fields are updatable."""
    category: ExpenseCategory | None = None
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = None
    spent_at: datetime | None = None


class ExpenseResponse(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    user_id: uuid.UUID
    wallet_id: uuid.UUID | None
    amount: Decimal
    currency: Currency
    category: ExpenseCategory
    title: str
    description: str | None
    spent_at: datetime
    deduct_from_wallet: bool
    transaction_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExpenseCategoryInfo(BaseModel):
    """Human-readable category listing."""
    value: str
    label: str

    @classmethod
    def all(cls) -> list["ExpenseCategoryInfo"]:
        return [
            cls(value=cat.value, label=EXPENSE_CATEGORY_LABELS[cat])
            for cat in ExpenseCategory
        ]
