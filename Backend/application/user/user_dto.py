from datetime import datetime

from pydantic import BaseModel


class CreateUserRequest(BaseModel):
    email: str
    name: str | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    name: str | None = None
    created_at: datetime | None = None
