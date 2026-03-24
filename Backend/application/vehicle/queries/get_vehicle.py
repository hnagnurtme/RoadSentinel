from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class GetVehicleQuery:
    vehicle_id: uuid.UUID
