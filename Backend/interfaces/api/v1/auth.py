from __future__ import annotations

from fastapi import APIRouter, Depends

from application.auth.login_command import LoginCommand
from application.auth.login_handler import LoginHandler
from application.user.user_dto import LoginRequest
from interfaces.api.deps import get_login_handler
from interfaces.api.response import success_response
from interfaces.api.v1.mappers import to_user_response

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(
    payload: LoginRequest,
    handler: LoginHandler = Depends(get_login_handler),
):
    token, user = handler.handle(
        LoginCommand(email=payload.email, password=payload.password)
    )
    return success_response(
        data={
            "access_token": token,
            "token_type": "bearer",
            "user": to_user_response(user).model_dump(by_alias=True),
        }
    )