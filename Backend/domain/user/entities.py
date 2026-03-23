from dataclasses import dataclass
from datetime import datetime

from domain.user.value_objects import EmailAddress


@dataclass
class UserEntity:
    email: EmailAddress
    name: str | None = None
    id: int | None = None
    created_at: datetime | None = None
