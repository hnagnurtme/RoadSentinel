from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class ListAlertsQuery:
    limit: int = 20
    driver_id: uuid.UUID | None = None
