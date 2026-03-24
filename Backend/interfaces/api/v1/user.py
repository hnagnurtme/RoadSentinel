from fastapi import APIRouter, Depends
import uuid

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
        id=user._id,
        email=user.email.value,
        name=user.name,
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


@router.post("")
def create_user(
    payload: CreateUserRequest,
    handler: CreateUserHandler = Depends(get_create_user_handler),
):
    user = handler.handle(
        CreateUserCommand(
            email=payload.email,
            name=payload.name,
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
        )
    )
    return success_response(data=_to_user_response(user).model_dump(by_alias=True))


@router.get("/{user_id}")
def get_user(
    user_id: uuid.UUID,
    handler: GetUserHandler = Depends(get_get_user_handler),
):
    user = handler.handle(GetUserQuery(user_id=user_id))
    return success_response(data=_to_user_response(user).model_dump(by_alias=True))
