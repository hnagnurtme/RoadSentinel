from __future__ import annotations

from passlib.hash import bcrypt

from application.auth.login_command import LoginCommand
from domain.user.entities import UserEntity
from domain.user.repository import UserRepository
from domain.user.value_objects import EmailAddress
from interfaces.api.jwt_tokens import create_access_token
from shared.exceptions import UnauthorizedException


class LoginHandler:
    def __init__(self, user_repository: UserRepository):
        self._users = user_repository

    def handle(self, command: LoginCommand) -> tuple[str, UserEntity]:
        email = EmailAddress(command.email)
        user = self._users.get_by_email(email.value)
        if user is None or not user.password_hash:
            raise UnauthorizedException("Invalid email or password")
        if not bcrypt.verify(command.password, user.password_hash):
            raise UnauthorizedException("Invalid email or password")

        token = create_access_token(user_id=user._id, role=user.role)  # type: ignore[arg-type]
        assert user._id is not None
        return token, user