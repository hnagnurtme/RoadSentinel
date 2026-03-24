from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class GetUserQuery:
    user_id: uuid.UUID
