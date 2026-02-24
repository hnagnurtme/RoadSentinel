from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from api.dependencies import CurrentUser
from constants import AuthDocs, Messages
from db.session import get_db
from schemas import ApiResponse
from schemas.auth import LoginRequest, RefreshTokenRequest, RegisterRequest, TokenResponse
from services import auth_service


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=ApiResponse[TokenResponse],
    status_code=status.HTTP_201_CREATED,
    summary=AuthDocs.Register.SUMMARY,
    description=AuthDocs.Register.DESCRIPTION,
)
async def register(
    data: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[TokenResponse]:
    token = await auth_service.register(db, data)
    return ApiResponse(message=Messages.USER_REGISTERED, data=token)


@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
    summary=AuthDocs.Login.SUMMARY,
    description=AuthDocs.Login.DESCRIPTION,
)
async def login(
    data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[TokenResponse]:
    token = await auth_service.login(db, data)
    return ApiResponse(message=Messages.LOGIN_SUCCESS, data=token)


@router.post(
    "/refresh",
    response_model=ApiResponse[TokenResponse],
    summary=AuthDocs.Refresh.SUMMARY,
    description=AuthDocs.Refresh.DESCRIPTION,
)
async def refresh(
    data: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[TokenResponse]:
    token = await auth_service.refresh_access_token(db, data.refresh_token)
    return ApiResponse(message=Messages.TOKEN_REFRESHED, data=token)


@router.post(
    "/logout",
    response_model=ApiResponse[None],
    summary=AuthDocs.Logout.SUMMARY,
    description=AuthDocs.Logout.DESCRIPTION,
)
async def logout(
    _current_user: CurrentUser,
) -> ApiResponse[None]:
    return ApiResponse(message=Messages.LOGOUT_SUCCESS, data=None)
