from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class CreateVehicleRequest(BaseModel):
    plate_number: str
    manufacturer: str | None = None
    model: str | None = None
    color: str | None = None
    production_year: int | None = None
    vin: str | None = None


class VehicleResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID = Field(serialization_alias="_id", validation_alias="_id")
    plate_number: str
    manufacturer: str | None = None
    model: str | None = None
    color: str | None = None
    production_year: int | None = None
    vin: str | None = None
    created_at: datetime | None = Field(default=None, serialization_alias="_created_at")
    updated_at: datetime | None = Field(default=None, serialization_alias="_updated_at")
    deleted_at: datetime | None = Field(default=None, serialization_alias="_deleted_at")
