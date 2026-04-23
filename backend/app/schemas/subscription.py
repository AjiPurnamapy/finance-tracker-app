import uuid
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

from app.core.constants import SubscriptionTier, SubscriptionStatus


class SubscriptionResponse(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    tier: SubscriptionTier
    status: SubscriptionStatus
    expires_at: Optional[datetime]
    max_seats: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
