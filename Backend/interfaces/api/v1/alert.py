"""REST endpoints for the Alert resource."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from application.alert.alert_dto import CreateAlertRequest
from application.alert.commands.create_alert import CreateAlertCommand
from application.alert.commands.create_alert_handler import CreateAlertHandler
from application.alert.commands.delete_alert import DeleteAlertCommand
from application.alert.commands.delete_alert_handler import DeleteAlertHandler
from application.alert.queries.get_alert import GetAlertQuery
from application.alert.queries.get_alert_handler import GetAlertHandler
from application.alert.queries.list_alerts_overview import ListAlertsOverviewQuery
from application.alert.queries.list_alerts_overview_handler import (
    ListAlertsOverviewHandler,
)
from infrastructure.repositories.user_repository_impl import UserRepositoryImpl
from infrastructure.repositories.vehicle_repository_impl import VehicleRepositoryImpl
from interfaces.api.deps import (
    get_create_alert_handler,
    get_delete_alert_handler,
    get_get_alert_handler,
    get_list_alerts_overview_handler,
    get_user_repository,
    get_vehicle_repository,
)
from interfaces.api.response import success_response
from interfaces.api.v1.mappers import (
    to_alert_response,
    to_user_response,
    to_vehicle_response,
)
from interfaces.api.v1.websocket import alerts_ws_manager

from interfaces.api.auth_dependencies import AuthTokenPayload, get_optional_auth_payload
from shared.exceptions import ForbiddenException

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _resolve_alert_relations(
    alert,
    user_repository: UserRepositoryImpl,
    vehicle_repository: VehicleRepositoryImpl,
):
    user = None
    vehicle = None

    if alert.driver_id is not None:
        user_entity = user_repository.get_by_id(alert.driver_id)
        if user_entity is not None:
            user = to_user_response(user_entity)

    if alert.vehicle_id is not None:
        vehicle_entity = vehicle_repository.get_by_id(alert.vehicle_id)
        if vehicle_entity is not None:
            vehicle = to_vehicle_response(vehicle_entity)

    return user, vehicle


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
    user, vehicle = _resolve_alert_relations(alert, user_repository, vehicle_repository)
    data = to_alert_response(alert, user=user, vehicle=vehicle).model_dump(
        by_alias=True
    )
    await alerts_ws_manager.broadcast({"event": "alert.created", "data": data})
    return success_response(data=data)


@router.get("")
def list_alerts(
    limit: int = Query(default=20, ge=1, le=100),
    driver_id: uuid.UUID | None = None,
    overview_handler: ListAlertsOverviewHandler = Depends(
        get_list_alerts_overview_handler
    ),
    auth: AuthTokenPayload | None = Depends(get_optional_auth_payload),
):
    effective_driver_id = driver_id
    if auth is not None and auth.role == "driver":
        effective_driver_id = auth.user_id

    data = overview_handler.handle(
        ListAlertsOverviewQuery(limit=limit, driver_id=effective_driver_id)
    )
    return success_response(data=data)


@router.get("/{alert_id}")
def get_alert(
    alert_id: uuid.UUID,
    handler: GetAlertHandler = Depends(get_get_alert_handler),
    user_repository: UserRepositoryImpl = Depends(get_user_repository),
    vehicle_repository: VehicleRepositoryImpl = Depends(get_vehicle_repository),
    auth: AuthTokenPayload | None = Depends(get_optional_auth_payload),
):
    alert = handler.handle(GetAlertQuery(alert_id=alert_id))
    if auth is not None and auth.role == "driver":
        if alert.driver_id != auth.user_id:
            raise ForbiddenException("Access denied")
    user, vehicle = _resolve_alert_relations(alert, user_repository, vehicle_repository)
    return success_response(
        data=to_alert_response(alert, user=user, vehicle=vehicle).model_dump(
            by_alias=True
        )
    )


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: uuid.UUID,
    handler: DeleteAlertHandler = Depends(get_delete_alert_handler),
    user_repository: UserRepositoryImpl = Depends(get_user_repository),
    vehicle_repository: VehicleRepositoryImpl = Depends(get_vehicle_repository),
):
    alert = handler.handle(DeleteAlertCommand(alert_id=alert_id))
    user, vehicle = _resolve_alert_relations(alert, user_repository, vehicle_repository)
    data = to_alert_response(alert, user=user, vehicle=vehicle).model_dump(
        by_alias=True
    )
    await alerts_ws_manager.broadcast({"event": "alert.deleted", "data": data})
    return success_response(data=data)
