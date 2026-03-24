from dataclasses import dataclass
from datetime import datetime
import uuid

from domain.alert.value_objects import AlertType


@dataclass
class AlertEntity:
    message: str
    alert_type: AlertType
    device_id: uuid.UUID
    driver_id: uuid.UUID | None = None
    vehicle_id: uuid.UUID | None = None
    evidence_url: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    _id: uuid.UUID | None = None
    _created_at: datetime | None = None
    _updated_at: datetime | None = None
    _deleted_at: datetime | None = None
