from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CreateUserCommand:
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
