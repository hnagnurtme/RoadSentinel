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
