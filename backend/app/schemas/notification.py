from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Any, Optional
from app.core.constants import NotificationType

import uuid

class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    type: NotificationType
    title: str
    message: str
    data: Optional[Any] = None
    is_read: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
