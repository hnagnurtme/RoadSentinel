from datetime import date
from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class CreateUserRequest(BaseModel):
    email: str
    name: str | None = None
    avatar_image_url: str | None = None
    name__family: str | None = None
    name__given: str | None = None
    name__middle: str | None = None
    name__prefix: str | None = None
    name__suffix: str | None = None
    birthday: date | None = None
    gender: str | None = None
    address__city: str | None = None
    address__country: str | None = None
    address__line1: str | None = None
    address__line2: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID = Field(serialization_alias="_id", validation_alias="_id")
    email: str
    name: str | None = None
    avatar_image_url: str | None = None
    name__family: str | None = None
    name__given: str | None = None
    name__middle: str | None = None
    name__prefix: str | None = None
    name__suffix: str | None = None
    birthday: date | None = None
    gender: str | None = None
    address__city: str | None = None
    address__country: str | None = None
    address__line1: str | None = None
    address__line2: str | None = None
    created_at: datetime | None = Field(default=None, serialization_alias="_created_at")
    updated_at: datetime | None = Field(default=None, serialization_alias="_updated_at")
    deleted_at: datetime | None = Field(default=None, serialization_alias="_deleted_at")
