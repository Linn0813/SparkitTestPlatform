from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.core.project_roles import parse_business_role
from app.models.project import BusinessProjectRole, ProjectRole
from app.schemas.common import ORMBase
from app.schemas.user import UserOut


class ProjectOut(ORMBase):
    id: str
    name: str
    is_enabled: bool
    created_at: datetime


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    is_enabled: Optional[bool] = None


class ProjectMemberOut(ORMBase):
    id: str
    project_id: str
    user_id: str
    role: BusinessProjectRole
    is_project_admin: bool
    user: Optional[UserOut] = None


class ProjectMemberAdd(BaseModel):
    user_id: str
    role: BusinessProjectRole = BusinessProjectRole.member
    is_project_admin: bool = False

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: BusinessProjectRole) -> BusinessProjectRole:
        parse_business_role(v, for_http=False)
        return v


class ProjectMemberUpdate(BaseModel):
    role: Optional[BusinessProjectRole] = None
    is_project_admin: Optional[bool] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[BusinessProjectRole]) -> Optional[BusinessProjectRole]:
        if v is None:
            return v
        parse_business_role(v, for_http=False)
        return v
