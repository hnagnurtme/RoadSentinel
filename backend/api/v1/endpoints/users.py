from fastapi import APIRouter

from api.dependencies import CurrentUser
from constants import Messages, UserDocs
from schemas import ApiResponse, UserResponse


router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=ApiResponse[UserResponse],
    summary=UserDocs.GetMe.SUMMARY,
    description=UserDocs.GetMe.DESCRIPTION,
)
async def get_current_user_profile(
    current_user: CurrentUser,
) -> ApiResponse[UserResponse]:
    return ApiResponse(
        message=Messages.USER_PROFILE_RETRIEVED,
        data=UserResponse.model_validate(current_user),
    )