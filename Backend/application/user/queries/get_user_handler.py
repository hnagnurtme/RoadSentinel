from application.user.queries.get_user import GetUserQuery
from domain.user.entities import UserEntity
from domain.user.repository import UserRepository
from shared.exceptions import NotFoundException


class GetUserHandler:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def handle(self, query: GetUserQuery) -> UserEntity:
        user = self.user_repository.get_by_id(query.user_id)
        if not user:
            raise NotFoundException("User not found")
        return user
