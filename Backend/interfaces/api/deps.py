from fastapi import Depends
from sqlalchemy.orm import Session

from application.user.commands.create_user_handler import CreateUserHandler
from application.user.queries.get_user_handler import GetUserHandler
from infrastructure.db.session import get_db
from infrastructure.repositories.user_repository_impl import UserRepositoryImpl


def get_user_repository(db: Session = Depends(get_db)) -> UserRepositoryImpl:
    return UserRepositoryImpl(db)


def get_create_user_handler(
    user_repository: UserRepositoryImpl = Depends(get_user_repository),
) -> CreateUserHandler:
    return CreateUserHandler(user_repository)


def get_get_user_handler(
    user_repository: UserRepositoryImpl = Depends(get_user_repository),
) -> GetUserHandler:
    return GetUserHandler(user_repository)
