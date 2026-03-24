from dataclasses import dataclass
from datetime import date
from datetime import datetime
import uuid

from domain.user.value_objects import EmailAddress


@dataclass
class UserEntity:
    email: EmailAddress
    name: str | None = None
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
    _id: uuid.UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
