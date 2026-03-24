from dataclasses import dataclass
from datetime import datetime
import uuid


@dataclass
class VehicleEntity:
    plate_number: str
    manufacturer: str | None = None
    model: str | None = None
    color: str | None = None
    production_year: int | None = None
    vin: str | None = None
    _id: uuid.UUID | None = None
    _created_at: datetime | None = None
    _updated_at: datetime | None = None
    _deleted_at: datetime | None = None
