import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class VehicleEntity:
    plate_number: str
    manufacturer: str | None = None
    model: str | None = None
    vehicle_image_url: str | None = None
    color: str | None = None
    production_year: int | None = None
    vin: str | None = None
    device_id: uuid.UUID | None = None
    _id: uuid.UUID | None = None
    _created_at: datetime | None = None
    _updated_at: datetime | None = None
    _deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        """Normalize plate number to uppercase for consistent storage and lookup."""
        if self.plate_number:
            self.plate_number = self.plate_number.strip().upper()
