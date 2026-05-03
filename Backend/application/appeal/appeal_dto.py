from datetime import datetime
from enum import Enum
import uuid

from pydantic import BaseModel, Field


class AppealStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class CreateAppealRequest(BaseModel):
    alert_id: uuid.UUID
    description: str | None = None
    attachment_url: str | None = None


class ReviewAppealRequest(BaseModel):
    status: AppealStatus
    admin_note: str | None = None


class AppealResponse(BaseModel):
    id: uuid.UUID = Field(serialization_alias="_id", validation_alias="_id")
    alert_id: uuid.UUID
    driver_id: uuid.UUID
    status: AppealStatus
    description: str | None = None
    attachment_url: str | None = None
    admin_note: str | None = None
    reviewed_by: uuid.UUID | None = None
    reviewed_at: datetime | None = None
    created_at: datetime | None = Field(default=None, serialization_alias="_created_at")
    updated_at: datetime | None = Field(default=None, serialization_alias="_updated_at")