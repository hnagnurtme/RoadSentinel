from typing import Annotated
from datetime import datetime
import uuid

from pydantic import (
    AnyUrl,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
)

from application.user.user_dto import UserResponse
from application.vehicle.vehicle_dto import VehicleResponse
from domain.alert.value_objects import AlertType


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def _validate_optional_url(value: str | None) -> str | None:
    normalized = _strip_or_none(value)
    if normalized is None:
        return None

    TypeAdapter(AnyUrl).validate_python(normalized)
    return normalized


MessageText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
OptionalUrl = Annotated[str | None, BeforeValidator(_validate_optional_url)]


class CreateAlertRequest(BaseModel):
    message: MessageText
    alert_type: AlertType = AlertType.DISTRACTED
    device_id: uuid.UUID
    driver_id: uuid.UUID | None = None
    vehicle_id: uuid.UUID | None = None
    evidence_url: OptionalUrl = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


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
    user: UserResponse | None = None
    vehicle: VehicleResponse | None = None
    created_at: datetime | None = Field(default=None, serialization_alias="_created_at")
    updated_at: datetime | None = Field(default=None, serialization_alias="_updated_at")
    deleted_at: datetime | None = Field(default=None, serialization_alias="_deleted_at")
