from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class GetAlertQuery:
    alert_id: uuid.UUID
