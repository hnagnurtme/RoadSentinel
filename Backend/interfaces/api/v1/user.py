"""
interfaces/api/v1/user.py
--------------------------
REST endpoints for the ``User`` resource.

Endpoints:
  POST  /users          — create a user
  GET   /users          — list all users
  GET   /users/{id}     — get a single user
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from application.user.commands.create_user import CreateUserCommand
from application.user.commands.create_user_handler import CreateUserHandler
from application.user.queries.get_user import GetUserQuery
from application.user.queries.get_user_handler import GetUserHandler
from application.user.queries.list_users import ListUsersQuery
from application.user.queries.list_users_handler import ListUsersHandler
from application.user.user_dto import CreateUserRequest
from interfaces.api.deps import (
    get_create_user_handler,
    get_get_user_handler,
    get_list_users_handler,
)
from interfaces.api.response import success_response
from interfaces.api.v1.mappers import to_user_response
from interfaces.api.auth_dependencies import AuthTokenPayload, require_auth_payload

router = APIRouter(prefix="/users", tags=["users"])


@router.post("")
def create_user(
    payload: CreateUserRequest,
    handler: CreateUserHandler = Depends(get_create_user_handler),
):
    user = handler.handle(
        CreateUserCommand(
            email=payload.email,
            name=payload.name,
            avatar_image_url=payload.avatar_image_url,
            name__family=payload.name__family,
            name__given=payload.name__given,
            name__middle=payload.name__middle,
            name__prefix=payload.name__prefix,
            name__suffix=payload.name__suffix,
            birthday=payload.birthday,
            gender=payload.gender,
            address__city=payload.address__city,
            address__country=payload.address__country,
            address__line1=payload.address__line1,
            address__line2=payload.address__line2,
            password_plain=payload.password,
            role=payload.role,
        )
    )
    return success_response(data=to_user_response(user).model_dump(by_alias=True))


@router.get("/me")
def get_me(
    auth: AuthTokenPayload = Depends(require_auth_payload),
    handler: GetUserHandler = Depends(get_get_user_handler),
):
    user = handler.handle(GetUserQuery(user_id=auth.user_id))
    return success_response(data=to_user_response(user).model_dump(by_alias=True))


@router.get("")
def list_users(handler: ListUsersHandler = Depends(get_list_users_handler)):
    users = handler.handle(ListUsersQuery())
    return success_response(
        data=[to_user_response(u).model_dump(by_alias=True) for u in users]
    )


@router.get("/{user_id}")
def get_user(
    user_id: uuid.UUID,
    handler: GetUserHandler = Depends(get_get_user_handler),
):
    user = handler.handle(GetUserQuery(user_id=user_id))
    return success_response(data=to_user_response(user).model_dump(by_alias=True))


from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi import HTTPException
from infrastructure.db.session import get_db
from infrastructure.db.models.user.tables import User, DrivingSession
from datetime import datetime, timezone, date
from interfaces.api.v1.websocket import frontend_mgr


class FingerprintRequest(BaseModel):
    fingerprint_id: str


@router.post("/fingerprint")
async def process_fingerprint(
    payload: FingerprintRequest, db: Session = Depends(get_db)
):
    # Tìm user dựa trên ID vân tay
    user = db.query(User).filter(User.fingerprint_id == payload.fingerprint_id).first()
    if not user:
        raise HTTPException(
            status_code=404, detail="Không tìm thấy tài xế với ID vân tay này"
        )

    # Kết thúc các phiên làm việc (driving session) cũ đang ACTIVE
    active_sessions = (
        db.query(DrivingSession)
        .filter(DrivingSession.user_id == user._id, DrivingSession.status == "ACTIVE")
        .all()
    )
    for s in active_sessions:
        s.status = "COMPLETED"
        s.ended_at = datetime.now(timezone.utc)

    # Tạo phiên lái xe mới
    new_session = DrivingSession(
        user_id=user._id,
        status="ACTIVE",
        _created_at=datetime.now(timezone.utc),
        _updated_at=datetime.now(timezone.utc),
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    # Gửi sự kiện qua WebSocket để frontend biết (realtime)
    import json

    await frontend_mgr.broadcast(
        json.dumps(
            {
                "type": "driving_session_started",
                "data": {
                    "driver_id": str(user._id),
                    "driver_name": user.name or user.email,
                    "session_id": str(new_session._id),
                    "fingerprint_id": payload.fingerprint_id,
                    "started_at": new_session._created_at.isoformat(),
                },
            }
        )
    )

    return success_response(
        data={
            "message": "Đã nhận diện tài xế thành công",
            "session_id": str(new_session._id),
            "driver_name": user.name or user.email,
        }
    )


class UpdateUserRequest(BaseModel):
    name: str | None = None
    avatar_image_url: str | None = None
    birthday: date | None = None
    gender: str | None = None
    address__city: str | None = None
    address__country: str | None = None
    fingerprint_id: str | None = None


@router.patch("/{user_id}")
def update_user(
    user_id: uuid.UUID, payload: UpdateUserRequest, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User._id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return success_response(data={"message": "User updated"})


class UpdateFingerprintRequest(BaseModel):
    fingerprint_id: str


@router.patch("/{user_id}/fingerprint")
def update_fingerprint(
    user_id: uuid.UUID, payload: UpdateFingerprintRequest, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User._id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.fingerprint_id = payload.fingerprint_id
    db.commit()
    return success_response(data={"message": "Fingerprint updated"})


@router.get("/{user_id}/driving-sessions")
def get_driving_sessions(user_id: uuid.UUID, db: Session = Depends(get_db)):
    sessions = (
        db.query(DrivingSession)
        .filter(DrivingSession.user_id == user_id)
        .order_by(DrivingSession._created_at.desc())
        .all()
    )
    data = []
    for s in sessions:
        data.append(
            {
                "id": str(s._id),
                "status": s.status,
                "started_at": s._created_at.isoformat(),
                "ended_at": s.ended_at.isoformat()
                if s.ended_at
                else (s._updated_at.isoformat() if s.status == "COMPLETED" else None),
            }
        )
    return success_response(data=data)
