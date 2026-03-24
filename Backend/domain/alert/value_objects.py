from dataclasses import dataclass
from enum import Enum

from shared.exceptions import ValidationException


class AlertType(str, Enum):
    SLEEPING = "SLEEPING"
    USING_PHONE = "USING_PHONE"
    DISTRACTED = "DISTRACTED"


@dataclass(frozen=True)
class Position:
    latitude: float | None = None
    longitude: float | None = None

    def __post_init__(self) -> None:
        if self.latitude is not None and not (-90.0 <= self.latitude <= 90.0):
            raise ValidationException("latitude must be between -90 and 90")
        if self.longitude is not None and not (-180.0 <= self.longitude <= 180.0):
            raise ValidationException("longitude must be between -180 and 180")
