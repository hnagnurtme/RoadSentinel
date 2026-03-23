from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.user.entities import UserEntity
from domain.user.repository import UserRepository
from domain.user.value_objects import EmailAddress
from infrastructure.db.models import User


class UserRepositoryImpl(UserRepository):
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _to_entity(row: User) -> UserEntity:
        return UserEntity(
            id=row.id,
            email=EmailAddress(row.email),
            name=row.name,
            created_at=row.created_at,
        )

    def create(self, user: UserEntity) -> UserEntity:
        row = User(email=user.email.value, name=user.name)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_entity(row)

    def get_by_id(self, user_id: int) -> UserEntity | None:
        stmt = select(User).where(User.id == user_id)
        row = self.db.execute(stmt).scalar_one_or_none()
        if not row:
            return None
        return self._to_entity(row)

    def get_by_email(self, email: str) -> UserEntity | None:
        stmt = select(User).where(User.email == email)
        row = self.db.execute(stmt).scalar_one_or_none()
        if not row:
            return None
        return self._to_entity(row)
