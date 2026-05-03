from fastapi import Depends
from sqlalchemy.orm import Session

from application.alert.commands.create_alert_handler import CreateAlertHandler
from application.alert.commands.delete_alert_handler import DeleteAlertHandler
from application.alert.queries.get_alert_handler import GetAlertHandler
from application.alert.queries.list_alerts_handler import ListAlertsHandler
from application.alert.queries.list_alerts_overview_handler import (
    ListAlertsOverviewHandler,
)
from application.user.commands.create_user_handler import CreateUserHandler
from application.user.queries.get_user_handler import GetUserHandler
from application.user.queries.list_users_handler import ListUsersHandler
from application.vehicle.commands.create_vehicle_handler import CreateVehicleHandler
from application.vehicle.queries.get_vehicle_handler import GetVehicleHandler
from application.vehicle.queries.list_vehicles_handler import ListVehiclesHandler
from infrastructure.db.session import get_db
from infrastructure.repositories.alert_repository_impl import AlertRepositoryImpl
from infrastructure.repositories.user_repository_impl import UserRepositoryImpl
from infrastructure.repositories.vehicle_repository_impl import VehicleRepositoryImpl

from application.auth.login_handler import LoginHandler


def get_user_repository(db: Session = Depends(get_db)) -> UserRepositoryImpl:
    return UserRepositoryImpl(db)


def get_alert_repository(db: Session = Depends(get_db)) -> AlertRepositoryImpl:
    return AlertRepositoryImpl(db)


def get_vehicle_repository(db: Session = Depends(get_db)) -> VehicleRepositoryImpl:
    return VehicleRepositoryImpl(db)


def get_create_user_handler(
    user_repository: UserRepositoryImpl = Depends(get_user_repository),
) -> CreateUserHandler:
    return CreateUserHandler(user_repository)


def get_get_user_handler(
    user_repository: UserRepositoryImpl = Depends(get_user_repository),
) -> GetUserHandler:
    return GetUserHandler(user_repository)


def get_list_users_handler(
    user_repository: UserRepositoryImpl = Depends(get_user_repository),
) -> ListUsersHandler:
    return ListUsersHandler(user_repository)


def get_create_alert_handler(
    alert_repository: AlertRepositoryImpl = Depends(get_alert_repository),
) -> CreateAlertHandler:
    return CreateAlertHandler(alert_repository)


def get_delete_alert_handler(
    alert_repository: AlertRepositoryImpl = Depends(get_alert_repository),
) -> DeleteAlertHandler:
    return DeleteAlertHandler(alert_repository)


def get_get_alert_handler(
    alert_repository: AlertRepositoryImpl = Depends(get_alert_repository),
) -> GetAlertHandler:
    return GetAlertHandler(alert_repository)


def get_list_alerts_handler(
    alert_repository: AlertRepositoryImpl = Depends(get_alert_repository),
) -> ListAlertsHandler:
    return ListAlertsHandler(alert_repository)


def get_list_alerts_overview_handler() -> ListAlertsOverviewHandler:
    return ListAlertsOverviewHandler()


def get_create_vehicle_handler(
    vehicle_repository: VehicleRepositoryImpl = Depends(get_vehicle_repository),
) -> CreateVehicleHandler:
    return CreateVehicleHandler(vehicle_repository)


def get_get_vehicle_handler(  
    vehicle_repository: VehicleRepositoryImpl = Depends(get_vehicle_repository),
) -> GetVehicleHandler:
    return GetVehicleHandler(vehicle_repository)


def get_list_vehicles_handler(
    vehicle_repository: VehicleRepositoryImpl = Depends(get_vehicle_repository),
) -> ListVehiclesHandler:
    return ListVehiclesHandler(vehicle_repository)

def get_login_handler(
    user_repository: UserRepositoryImpl = Depends(get_user_repository),
) -> LoginHandler:
    return LoginHandler(user_repository)
