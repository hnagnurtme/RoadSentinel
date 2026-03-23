from dataclasses import dataclass

from shared.exceptions import ValidationException


@dataclass(frozen=True)
class EmailAddress:
    value: str

    def __post_init__(self):
        email = self.value.strip().lower()
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise ValidationException("Invalid email format")
        object.__setattr__(self, "value", email)
