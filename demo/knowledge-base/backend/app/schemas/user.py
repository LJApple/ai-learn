"""User related schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: str | None = Field(None, max_length=100)


class UserCreate(UserBase):
    """User creation schema."""

    password: str = Field(..., min_length=8, max_length=100)
    department_id: uuid.UUID | None = None


class UserUpdate(BaseModel):
    """User update schema."""

    email: EmailStr | None = None
    full_name: str | None = Field(None, max_length=100)
    department_id: uuid.UUID | None = None
    is_active: bool | None = None


class UserLogin(BaseModel):
    """User login schema."""

    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)


class UserResponse(UserBase):
    """User response schema."""

    id: uuid.UUID
    department_id: uuid.UUID | None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
