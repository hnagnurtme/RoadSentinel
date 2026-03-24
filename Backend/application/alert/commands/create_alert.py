from dataclasses import dataclass
import uuid

from domain.alert.value_objects import AlertType


@dataclass(frozen=True)
class CreateAlertCommand:
    message: str
    alert_type: AlertType
    device_id: uuid.UUID
    driver_id: uuid.UUID | None = None
    vehicle_id: uuid.UUID | None = None
    evidence_url: str | None = None
    latitude: float | None = None
    longitude: float | None = None
