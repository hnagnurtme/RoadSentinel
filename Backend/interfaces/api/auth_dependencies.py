from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from interfaces.api.jwt_tokens import decode_access_token
from shared.exceptions import ForbiddenException, UnauthorizedException

_bearer = HTTPBearer(auto_error=False)


class AuthTokenPayload:
    __slots__ = ("user_id", "role")

    def __init__(self, user_id: uuid.UUID, role: str) -> None:
        self.user_id = user_id
        self.role = role


def _payload_from_credentials(
    credentials: HTTPAuthorizationCredentials | None,
    *,
    optional: bool,
) -> AuthTokenPayload | None:
    if credentials is None or not credentials.credentials:
        if optional:
            return None
        raise UnauthorizedException("Not authenticated")

    data = decode_access_token(credentials.credentials)
    sub = data.get("sub")
    role = data.get("role")
    if not sub or role not in ("admin", "driver"):
        raise UnauthorizedException("Invalid token payload")

    try:
        uid = uuid.UUID(str(sub))
    except ValueError as e:
        raise UnauthorizedException("Invalid token subject") from e

    return AuthTokenPayload(uid, str(role))


def get_optional_auth_payload(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ] = None,
) -> AuthTokenPayload | None:
    return _payload_from_credentials(credentials, optional=True)


def require_auth_payload(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ] = None,
) -> AuthTokenPayload:
    payload = _payload_from_credentials(credentials, optional=False)
    assert payload is not None
    return payload


def require_admin_payload(
    auth: Annotated[AuthTokenPayload, Depends(require_auth_payload)],
) -> AuthTokenPayload:
    if auth.role != "admin":
        raise ForbiddenException("Admin access required")
    return auth