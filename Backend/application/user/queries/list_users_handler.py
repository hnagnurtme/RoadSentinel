from application.user.queries.list_users import ListUsersQuery
from domain.user.entities import UserEntity
from domain.user.repository import UserRepository


class ListUsersHandler:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def handle(self, query: ListUsersQuery) -> list[UserEntity]:
        return self.user_repository.list_all()
