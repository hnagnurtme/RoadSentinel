from typing import Annotated, Literal
from datetime import date
from datetime import datetime
import uuid

from pydantic import (
    AnyUrl,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    TypeAdapter,
)


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


def _normalize_and_validate_email(value: str) -> str:
    email = value.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValueError("invalid email format")
    return email


EmailText = Annotated[str, BeforeValidator(_normalize_and_validate_email)]
OptionalText = Annotated[str | None, BeforeValidator(_strip_or_none)]
OptionalUrl = Annotated[str | None, BeforeValidator(_validate_optional_url)]


class CreateUserRequest(BaseModel):
    email: EmailText
    name: OptionalText = None
    avatar_image_url: OptionalUrl = None
    name__family: OptionalText = None
    name__given: OptionalText = None
    name__middle: OptionalText = None
    name__prefix: OptionalText = None
    name__suffix: OptionalText = None
    birthday: date | None = None
    gender: OptionalText = None
    address__city: OptionalText = None
    address__country: OptionalText = None
    address__line1: OptionalText = None
    address__line2: OptionalText = None
    password: Annotated[str | None, Field(default=None, min_length=8)] = None
    role: Literal["admin", "driver"] = "driver"


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
    role: str = "driver"
    fingerprint_id: str | None = None
    
class LoginRequest(BaseModel):
    email: EmailText
    password: str = Field(min_length=1)
