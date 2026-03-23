from dataclasses import dataclass


@dataclass(frozen=True)
class CreateUserCommand:
	email: str
	name: str | None = None

