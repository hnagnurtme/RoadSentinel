from __future__ import annotations

from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from application.appeal.appeal_dto import (
    AppealResponse,
    AppealStatus,
    CreateAppealRequest,
    ReviewAppealRequest,
)
from infrastructure.db.models.alert.tables import Alert, Appeal
from infrastructure.db.session import get_db
from interfaces.api.auth_dependencies import (
    AuthTokenPayload,
    require_admin_payload,
    require_auth_payload,
)
from interfaces.api.response import success_response
from interfaces.api.v1.websocket import appeals_ws_manager
from shared.exceptions import ForbiddenException, NotFoundException, ValidationException

router = APIRouter(prefix="/appeals", tags=["appeals"])


def to_response(row: Appeal) -> dict:
    return AppealResponse(
        _id=row._id,
        alert_id=row.alert_id,
        driver_id=row.driver_id,
        status=row.status.value if hasattr(row.status, "value") else row.status,
        description=row.description,
        attachment_url=row.attachment_url,
        admin_note=row.admin_note,
        reviewed_by=row.reviewed_by,
        reviewed_at=row.reviewed_at,
        created_at=row._created_at,
        updated_at=row._updated_at,
    ).model_dump(by_alias=True, mode="json")


@router.post("")
async def create_appeal(
    payload: CreateAppealRequest,
    auth: AuthTokenPayload = Depends(require_auth_payload),
    db: Session = Depends(get_db),
):
    if auth.role != "driver":
        raise ForbiddenException("Only drivers can submit appeals")

    alert = db.execute(
        select(Alert).where(Alert._id == payload.alert_id, Alert._deleted_at.is_(None))
    ).scalar_one_or_none()
    if alert is None:
        raise NotFoundException("Alert not found")
    if alert.driver_id != auth.user_id:
        raise ForbiddenException("You can only appeal your own alerts")

    existing_pending = db.execute(
        select(Appeal).where(
            Appeal.alert_id == payload.alert_id,
            Appeal.driver_id == auth.user_id,
            Appeal.status == AppealStatus.PENDING,
            Appeal._deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if existing_pending is not None:
        raise ValidationException("A pending appeal already exists for this alert")

    row = Appeal(
        alert_id=payload.alert_id,
        driver_id=auth.user_id,
        status=AppealStatus.PENDING,
        description=payload.description,
        attachment_url=payload.attachment_url,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    payload = to_response(row)
    await appeals_ws_manager.broadcast({"event": "appeal.created", "data": payload})
    return success_response(data=payload)


@router.get("/my")
def list_my_appeals(
    auth: AuthTokenPayload = Depends(require_auth_payload),
    db: Session = Depends(get_db),
):
    if auth.role != "driver":
        raise ForbiddenException("Only drivers can access this endpoint")

    rows = db.execute(
        select(Appeal)
        .where(Appeal.driver_id == auth.user_id, Appeal._deleted_at.is_(None))
        .order_by(Appeal._created_at.desc())
    ).scalars().all()
    return success_response(data=[to_response(row) for row in rows])


@router.get("")
def list_appeals_admin(
    _: AuthTokenPayload = Depends(require_admin_payload),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(Appeal)
        .where(Appeal._deleted_at.is_(None))
        .order_by(Appeal._created_at.desc())
    ).scalars().all()
    return success_response(data=[to_response(row) for row in rows])


@router.patch("/{appeal_id}/review")
async def review_appeal(
    appeal_id: uuid.UUID,
    payload: ReviewAppealRequest,
    admin: AuthTokenPayload = Depends(require_admin_payload),
    db: Session = Depends(get_db),
):
    if payload.status == AppealStatus.PENDING:
        raise ValidationException("Review status cannot be PENDING")

    row = db.execute(
        select(Appeal).where(Appeal._id == appeal_id, Appeal._deleted_at.is_(None))
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundException("Appeal not found")

    row.status = payload.status
    row.admin_note = payload.admin_note
    row.reviewed_by = admin.user_id
    row.reviewed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(row)
    payload = to_response(row)
    await appeals_ws_manager.broadcast({"event": "appeal.reviewed", "data": payload})
    return success_response(data=payload)