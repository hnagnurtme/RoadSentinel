from fastapi import APIRouter
from constants import  UserDocs, Messages
from  schemas import UserResponse , ApiResponse


router = APIRouter(prefix="/users", tags=["Users"])

@router.get(
    "/me",
    response_model=ApiResponse[UserResponse],
    summary=UserDocs.GetMe.SUMMARY,
    description=UserDocs.GetMe.DESCRIPTION,
)
async def get_current_user_profile(

) -> ApiResponse[UserResponse]:
    return ApiResponse(
        message=Messages.USER_PROFILE_RETRIEVED,
        data="OK"
    )