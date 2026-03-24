from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field

from domain.alert.value_objects import AlertType


class CreateAlertRequest(BaseModel):
    message: str
    alert_type: AlertType = AlertType.DISTRACTED
    device_id: uuid.UUID
    driver_id: uuid.UUID | None = None
    vehicle_id: uuid.UUID | None = None
    evidence_url: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class AlertResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID = Field(serialization_alias="_id", validation_alias="_id")
    message: str
    alert_type: AlertType
    device_id: uuid.UUID
    driver_id: uuid.UUID | None = None
    vehicle_id: uuid.UUID | None = None
    evidence_url: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    created_at: datetime | None = Field(default=None, serialization_alias="_created_at")
    updated_at: datetime | None = Field(default=None, serialization_alias="_updated_at")
    deleted_at: datetime | None = Field(default=None, serialization_alias="_deleted_at")
