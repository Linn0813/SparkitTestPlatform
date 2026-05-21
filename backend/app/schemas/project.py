from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.project import ProjectRole
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
    role: ProjectRole
    user: Optional[UserOut] = None


class ProjectMemberAdd(BaseModel):
    user_id: str
    role: ProjectRole = ProjectRole.member
