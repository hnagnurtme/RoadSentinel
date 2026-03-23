from application.user.commands.create_user import CreateUserCommand
from domain.user.entities import UserEntity
from domain.user.repository import UserRepository
from domain.user.services import UserDomainService
from domain.user.value_objects import EmailAddress


class CreateUserHandler:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        self.domain_service = UserDomainService(user_repository)

    def handle(self, command: CreateUserCommand) -> UserEntity:
        email = EmailAddress(command.email)
        self.domain_service.ensure_email_available(email)

        user = UserEntity(email=email, name=command.name)
        return self.user_repository.create(user)
