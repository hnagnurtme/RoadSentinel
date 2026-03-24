from fastapi import APIRouter, Depends, Query
import uuid

from application.alert.alert_dto import AlertResponse, CreateAlertRequest
from application.user.user_dto import UserResponse
from application.vehicle.vehicle_dto import VehicleResponse
from application.alert.commands.create_alert import CreateAlertCommand
from application.alert.commands.create_alert_handler import CreateAlertHandler
from application.alert.queries.get_alert import GetAlertQuery
from application.alert.queries.get_alert_handler import GetAlertHandler
from application.alert.queries.list_alerts import ListAlertsQuery
from application.alert.queries.list_alerts_handler import ListAlertsHandler
from interfaces.api.deps import (
    get_create_alert_handler,
    get_get_alert_handler,
    get_list_alerts_handler,
    get_user_repository,
    get_vehicle_repository,
)
from interfaces.api.response import success_response
from interfaces.api.v1.websocket import alerts_ws_manager
from infrastructure.repositories.user_repository_impl import UserRepositoryImpl
from infrastructure.repositories.vehicle_repository_impl import VehicleRepositoryImpl

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _to_user_response(user) -> UserResponse:
    return UserResponse(
        id=user._id,
        email=user.email.value,
        name=user.name,
        avatar_image_url=user.avatar_image_url,
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
        created_at=user.created_at,
        updated_at=user.updated_at,
        deleted_at=user.deleted_at,
    )


def _to_vehicle_response(vehicle) -> VehicleResponse:
    return VehicleResponse(
        id=vehicle._id,
        plate_number=vehicle.plate_number,
        manufacturer=vehicle.manufacturer,
        model=vehicle.model,
        vehicle_image_url=vehicle.vehicle_image_url,
        color=vehicle.color,
        production_year=vehicle.production_year,
        vin=vehicle.vin,
        created_at=vehicle._created_at,
        updated_at=vehicle._updated_at,
        deleted_at=vehicle._deleted_at,
    )


def _resolve_alert_relations(
    alert,
    user_repository: UserRepositoryImpl,
    vehicle_repository: VehicleRepositoryImpl,
) -> tuple[UserResponse | None, VehicleResponse | None]:
    user_response: UserResponse | None = None
    vehicle_response: VehicleResponse | None = None

    if alert.driver_id is not None:
        user = user_repository.get_by_id(alert.driver_id)
        if user is not None:
            user_response = _to_user_response(user)

    if alert.vehicle_id is not None:
        vehicle = vehicle_repository.get_by_id(alert.vehicle_id)
        if vehicle is not None:
            vehicle_response = _to_vehicle_response(vehicle)

    return user_response, vehicle_response


def _to_alert_response(
    alert,
    user: UserResponse | None = None,
    vehicle: VehicleResponse | None = None,
) -> AlertResponse:
    return AlertResponse(
        id=alert._id,
        message=alert.message,
        alert_type=alert.alert_type,
        device_id=alert.device_id,
        driver_id=alert.driver_id,
        vehicle_id=alert.vehicle_id,
        evidence_url=alert.evidence_url,
        latitude=alert.latitude,
        longitude=alert.longitude,
        user=user,
        vehicle=vehicle,
        created_at=alert._created_at,
        updated_at=alert._updated_at,
        deleted_at=alert._deleted_at,
    )


@router.post("")
async def create_alert(
    payload: CreateAlertRequest,
    handler: CreateAlertHandler = Depends(get_create_alert_handler),
    user_repository: UserRepositoryImpl = Depends(get_user_repository),
    vehicle_repository: VehicleRepositoryImpl = Depends(get_vehicle_repository),
):
    alert = handler.handle(
        CreateAlertCommand(
            message=payload.message,
            alert_type=payload.alert_type,
            device_id=payload.device_id,
            driver_id=payload.driver_id,
            vehicle_id=payload.vehicle_id,
            evidence_url=payload.evidence_url,
            latitude=payload.latitude,
            longitude=payload.longitude,
        )
    )
    user, vehicle = _resolve_alert_relations(
        alert=alert,
        user_repository=user_repository,
        vehicle_repository=vehicle_repository,
    )
    data = _to_alert_response(alert, user=user, vehicle=vehicle).model_dump(
        by_alias=True
    )
    await alerts_ws_manager.broadcast(
        {
            "event": "alert.created",
            "data": data,
        }
    )
    return success_response(data=data)


@router.get("/{alert_id}")
def get_alert(
    alert_id: uuid.UUID,
    handler: GetAlertHandler = Depends(get_get_alert_handler),
    user_repository: UserRepositoryImpl = Depends(get_user_repository),
    vehicle_repository: VehicleRepositoryImpl = Depends(get_vehicle_repository),
):
    alert = handler.handle(GetAlertQuery(alert_id=alert_id))
    user, vehicle = _resolve_alert_relations(
        alert=alert,
        user_repository=user_repository,
        vehicle_repository=vehicle_repository,
    )
    return success_response(
        data=_to_alert_response(alert, user=user, vehicle=vehicle).model_dump(
            by_alias=True
        )
    )


@router.get("")
def list_alerts(
    limit: int = Query(default=20, ge=1, le=100),
    driver_id: uuid.UUID | None = None,
    handler: ListAlertsHandler = Depends(get_list_alerts_handler),
    user_repository: UserRepositoryImpl = Depends(get_user_repository),
    vehicle_repository: VehicleRepositoryImpl = Depends(get_vehicle_repository),
):
    alerts = handler.handle(ListAlertsQuery(limit=limit, driver_id=driver_id))
    data = []
    for alert in alerts:
        user, vehicle = _resolve_alert_relations(
            alert=alert,
            user_repository=user_repository,
            vehicle_repository=vehicle_repository,
        )
        data.append(
            _to_alert_response(alert, user=user, vehicle=vehicle).model_dump(
                by_alias=True
            )
        )

    return success_response(data=data)
