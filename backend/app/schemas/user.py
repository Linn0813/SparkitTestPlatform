from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMBase


class UserOut(ORMBase):
    id: str
    email: str
    name: str
    is_active: bool
    is_system_admin: bool
    last_project_id: Optional[str]
    wecom_mobile: Optional[str] = None
    wecom_userid: Optional[str] = None
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=6)
    is_active: bool = True
    is_system_admin: bool = False


class UserUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    is_system_admin: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=6)


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6)


class UserProfileUpdate(BaseModel):
    wecom_mobile: Optional[str] = Field(default=None, max_length=32)
    wecom_userid: Optional[str] = Field(default=None, max_length=128)
