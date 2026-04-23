from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from datetime import datetime
from typing import Optional

class SavingsGoalBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    target_amount: Decimal = Field(..., gt=0)

class SavingsGoalCreate(SavingsGoalBase):
    pass

class SavingsGoalUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    target_amount: Optional[Decimal] = Field(None, gt=0)

class SavingsGoalContribute(BaseModel):
    amount: Decimal = Field(..., gt=0)

import uuid

class SavingsGoalResponse(SavingsGoalBase):
    id: uuid.UUID
    user_id: uuid.UUID
    current_amount: Decimal
    is_completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
