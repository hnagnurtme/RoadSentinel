from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class DeleteAlertCommand:
    alert_id: uuid.UUID
