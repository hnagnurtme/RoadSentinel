import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
)
from exceptions.auth import UnauthorizedException
from exceptions.base import AppException
from models.organization import Organization
from schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from services import user_service


async def register(db: AsyncSession, data: RegisterRequest) -> TokenResponse:
    """Register a new user, optionally creating an organization."""
    # Check for existing email
    existing = await user_service.get_by_email(db, data.email)
    if existing:
        raise AppException(
            message="Email is already registered",
            status_code=409,
            error_code="EMAIL_ALREADY_EXISTS",
        )

    # Create organisation if provided
    org_id: int | None = None
    if data.organization_name:
        org = Organization(name=data.organization_name)
        db.add(org)
        await db.flush()
        org_id = org.id

    # Validate password length in UTF-8 bytes before hashing
    if len(data.password.encode("utf-8")) > 72:
        raise AppException(
            message="Password is too long",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="PASSWORD_TOO_LONG",
        )

    # Create user
    user = await user_service.create(
        db,
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        organization_id=org_id,
    )

    return TokenResponse(
        user_id=user.id,
        user_email=user.email,
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
    )


async def login(db: AsyncSession, data: LoginRequest) -> TokenResponse:
    """Authenticate user credentials and return JWT pair."""
    user = await user_service.get_by_email(db, data.email)

    if not user or not verify_password(data.password, user.hashed_password):
        raise UnauthorizedException("Invalid email or password")

    if not user.is_active:
        raise AppException(
            message="User account is deactivated",
            status_code=403,
            error_code="ACCOUNT_DEACTIVATED",
        )

    return TokenResponse(
        user_id=user.id,
        user_email=user.email,
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
    )


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> TokenResponse:
    """Validate refresh token and issue a new access token."""
    import jwt as _jwt
    from core.security import decode_token
    from exceptions.auth import UnauthorizedException

    try:
        payload = decode_token(refresh_token)
    except _jwt.ExpiredSignatureError:
        raise AppException(
            message="Refresh token has expired",
            status_code=401,
            error_code="TOKEN_EXPIRED",
        )
    except _jwt.InvalidTokenError:
        raise UnauthorizedException("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid token type")

    user_id = int(payload["sub"])
    user = await user_service.get_by_id(db, user_id)
    if not user or not user.is_active:
        raise UnauthorizedException()

    return TokenResponse(
        user_id=user.id,
        user_email=user.email,
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
    )
