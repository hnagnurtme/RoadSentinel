from dataclasses import dataclass


@dataclass(frozen=True)
class GetUserQuery:
    user_id: int
