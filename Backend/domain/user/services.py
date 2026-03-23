from domain.user.repository import UserRepository
from domain.user.value_objects import EmailAddress
from shared.exceptions import ConflictException


class UserDomainService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def ensure_email_available(self, email: EmailAddress) -> None:
        existing = self.user_repository.get_by_email(email.value)
        if existing:
            raise ConflictException("Email already exists")
