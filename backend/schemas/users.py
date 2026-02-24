from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr


class OrganizationInfo(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    organization: OrganizationInfo | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
