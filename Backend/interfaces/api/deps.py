from fastapi import Depends
from sqlalchemy.orm import Session

from application.alert.commands.create_alert_handler import CreateAlertHandler
from application.alert.queries.get_alert_handler import GetAlertHandler
from application.alert.queries.list_alerts_handler import ListAlertsHandler
from application.user.commands.create_user_handler import CreateUserHandler
from application.user.queries.get_user_handler import GetUserHandler
from infrastructure.db.session import get_db
from infrastructure.repositories.alert_repository_impl import AlertRepositoryImpl
from infrastructure.repositories.user_repository_impl import UserRepositoryImpl


def get_user_repository(db: Session = Depends(get_db)) -> UserRepositoryImpl:
    return UserRepositoryImpl(db)


def get_alert_repository(db: Session = Depends(get_db)) -> AlertRepositoryImpl:
    return AlertRepositoryImpl(db)


def get_create_user_handler(
    user_repository: UserRepositoryImpl = Depends(get_user_repository),
) -> CreateUserHandler:
    return CreateUserHandler(user_repository)


def get_get_user_handler(
    user_repository: UserRepositoryImpl = Depends(get_user_repository),
) -> GetUserHandler:
    return GetUserHandler(user_repository)


def get_create_alert_handler(
    alert_repository: AlertRepositoryImpl = Depends(get_alert_repository),
) -> CreateAlertHandler:
    return CreateAlertHandler(alert_repository)


def get_get_alert_handler(
    alert_repository: AlertRepositoryImpl = Depends(get_alert_repository),
) -> GetAlertHandler:
    return GetAlertHandler(alert_repository)


def get_list_alerts_handler(
    alert_repository: AlertRepositoryImpl = Depends(get_alert_repository),
) -> ListAlertsHandler:
    return ListAlertsHandler(alert_repository)
