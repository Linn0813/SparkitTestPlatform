from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class VersionBrief(ORMBase):
    id: str
    num: int
    name: str


class ProjectVersionOut(ORMBase):
    id: str
    project_id: str
    num: int
    name: str
    released_at: Optional[date] = None
    created_by: str
    created_at: datetime
    updated_at: datetime


class ProjectVersionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    released_at: Optional[date] = None


class ProjectVersionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    released_at: Optional[date] = None
