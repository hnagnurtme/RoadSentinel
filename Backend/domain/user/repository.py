from abc import ABC, abstractmethod
import uuid

from domain.user.entities import UserEntity


class UserRepository(ABC):
    @abstractmethod
    def create(self, user: UserEntity) -> UserEntity:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, user_id: uuid.UUID) -> UserEntity | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_email(self, email: str) -> UserEntity | None:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[UserEntity]:
        raise NotImplementedError
