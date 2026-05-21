from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserOut


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SwitchContextRequest(BaseModel):
    project_id: Optional[str] = None


class MeResponse(BaseModel):
    user: UserOut
    projects: list["ProjectBrief"]


class ProjectBrief(BaseModel):
    id: str
    name: str
    role: Optional[str] = None


MeResponse.model_rebuild()
