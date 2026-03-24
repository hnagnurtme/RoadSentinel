from fastapi import APIRouter, Depends, Query
import uuid

from application.alert.alert_dto import AlertResponse, CreateAlertRequest
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
)
from interfaces.api.response import success_response

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _to_alert_response(alert) -> AlertResponse:
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
        created_at=alert._created_at,
        updated_at=alert._updated_at,
        deleted_at=alert._deleted_at,
    )


@router.post("")
def create_alert(
    payload: CreateAlertRequest,
    handler: CreateAlertHandler = Depends(get_create_alert_handler),
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
    return success_response(data=_to_alert_response(alert).model_dump(by_alias=True))


@router.get("/{alert_id}")
def get_alert(
    alert_id: uuid.UUID,
    handler: GetAlertHandler = Depends(get_get_alert_handler),
):
    alert = handler.handle(GetAlertQuery(alert_id=alert_id))
    return success_response(data=_to_alert_response(alert).model_dump(by_alias=True))


@router.get("")
def list_alerts(
    limit: int = Query(default=20, ge=1, le=100),
    driver_id: uuid.UUID | None = None,
    handler: ListAlertsHandler = Depends(get_list_alerts_handler),
):
    alerts = handler.handle(ListAlertsQuery(limit=limit, driver_id=driver_id))
    return success_response(
        data=[_to_alert_response(alert).model_dump(by_alias=True) for alert in alerts]
    )
