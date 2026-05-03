from dataclasses import dataclass


@dataclass(frozen=True)
class LoginCommand:
    email: str
    password: str