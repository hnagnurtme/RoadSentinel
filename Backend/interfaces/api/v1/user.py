from fastapi import APIRouter, Depends

from application.user.commands.create_user import CreateUserCommand
from application.user.commands.create_user_handler import CreateUserHandler
from application.user.queries.get_user import GetUserQuery
from application.user.queries.get_user_handler import GetUserHandler
from application.user.user_dto import CreateUserRequest, UserResponse
from interfaces.api.deps import get_create_user_handler, get_get_user_handler
from interfaces.api.response import success_response

router = APIRouter(prefix="/users", tags=["users"])


def _to_user_response(user) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email.value,
        name=user.name,
        created_at=user.created_at,
    )


@router.post("")
def create_user(
    payload: CreateUserRequest,
    handler: CreateUserHandler = Depends(get_create_user_handler),
):
    user = handler.handle(CreateUserCommand(email=payload.email, name=payload.name))
    return success_response(data=_to_user_response(user).dict())


@router.get("/{user_id}")
def get_user(
    user_id: int,
    handler: GetUserHandler = Depends(get_get_user_handler),
):
    user = handler.handle(GetUserQuery(user_id=user_id))
    return success_response(data=_to_user_response(user).dict())
