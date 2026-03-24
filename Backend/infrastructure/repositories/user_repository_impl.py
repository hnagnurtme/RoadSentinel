from sqlalchemy import select
from sqlalchemy.orm import Session
import uuid

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
            _id=row._id,
            email=EmailAddress(row.email),
            name=row.name,
            name__family=row.name__family,
            name__given=row.name__given,
            name__middle=row.name__middle,
            name__prefix=row.name__prefix,
            name__suffix=row.name__suffix,
            birthday=row.birthday,  # type: ignore
            gender=row.gender,
            address__city=row.address__city,
            address__country=row.address__country,
            address__line1=row.address__line1,
            address__line2=row.address__line2,
            created_at=row._created_at,
            updated_at=row._updated_at,
            deleted_at=row._deleted_at,
        )

    def create(self, user: UserEntity) -> UserEntity:
        row = User(
            email=user.email.value,
            name=user.name,
            name__family=user.name__family,
            name__given=user.name__given,
            name__middle=user.name__middle,
            name__prefix=user.name__prefix,
            name__suffix=user.name__suffix,
            birthday=user.birthday,
            gender=user.gender,
            address__city=user.address__city,
            address__country=user.address__country,
            address__line1=user.address__line1,
            address__line2=user.address__line2,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_entity(row)

    def get_by_id(self, user_id: uuid.UUID) -> UserEntity | None:
        stmt = select(User).where(User._id == user_id)
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
