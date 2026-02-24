import hashlib
import jwt
from datetime import datetime, timedelta, timezone
from typing import Any

from passlib.context import CryptContext
from core.config import settings

# ─── Password Hashing ────────────────────────────────────────────────────────

# Khởi tạo context với bcrypt. 
# Lưu ý: Cần cài đặt bcrypt==4.0.1 để tương thích với Python 3.13
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password using SHA-256 pre-hashing followed by bcrypt.
    This bypasses the 72-byte limit of bcrypt and maintains security.
    """
    # Bước 1: Băm SHA-256 để đưa mọi mật khẩu về độ dài cố định (64 ký tự hex)
    pre_hash = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()

    # Bước 2: Đưa chuỗi đã băm vào Bcrypt
    return _pwd_context.hash(pre_hash)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a bcrypt hash by applying 
    the same SHA-256 pre-hashing logic.
    """
    pre_hash = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    return _pwd_context.verify(pre_hash, hashed_password)


# ─── JWT ─────────────────────────────────────────────────────────────────────

ALGORITHM = "HS256"


def create_access_token(
        data: dict[str, Any],
        expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.
    Uses timezone-aware datetime for compatibility with Python 3.13.
    """
    expire = datetime.now(timezone.utc) + (
            expires_delta
            or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    # Gắn thêm type để phân biệt với refresh token
    payload = {**data, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    """
    Create a JWT refresh token with a longer lifespan.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {**data, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.
    Returns the payload if valid, otherwise raises an exception.
    """
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])