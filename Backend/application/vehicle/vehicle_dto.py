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


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def _strip_upper_or_none(value: str | None) -> str | None:
    normalized = _strip_or_none(value)
    return normalized.upper() if normalized is not None else None


def _validate_optional_url(value: str | None) -> str | None:
    normalized = _strip_or_none(value)
    if normalized is None:
        return None

    TypeAdapter(AnyUrl).validate_python(normalized)
    return normalized


PlateNumber = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_upper=True, min_length=1),
]
OptionalText = Annotated[str | None, BeforeValidator(_strip_or_none)]
OptionalUpperText = Annotated[str | None, BeforeValidator(_strip_upper_or_none)]
OptionalUrl = Annotated[str | None, BeforeValidator(_validate_optional_url)]


class CreateVehicleRequest(BaseModel):
    plate_number: PlateNumber
    manufacturer: OptionalText = None
    model: OptionalText = None
    vehicle_image_url: OptionalUrl = None
    color: OptionalText = None
    production_year: int | None = Field(default=None, ge=1900, le=2100)
    vin: Annotated[OptionalUpperText, Field(max_length=17)] = None
    device_id: uuid.UUID | None = None


class VehicleResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID = Field(serialization_alias="_id", validation_alias="_id")
    plate_number: str
    manufacturer: str | None = None
    model: str | None = None
    vehicle_image_url: str | None = None
    color: str | None = None
    production_year: int | None = None
    vin: str | None = None
    device_id: uuid.UUID | None = None
    created_at: datetime | None = Field(default=None, serialization_alias="_created_at")
    updated_at: datetime | None = Field(default=None, serialization_alias="_updated_at")
    deleted_at: datetime | None = Field(default=None, serialization_alias="_deleted_at")
