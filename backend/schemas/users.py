from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
