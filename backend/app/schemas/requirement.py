from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.requirement import RequirementStatus
from app.schemas.common import ORMBase
from app.schemas.version import VersionBrief


class RequirementOut(ORMBase):
    id: str
    project_id: str
    num: int
    title: str
    external_url: Optional[str]
    version_id: Optional[str] = None
    version: Optional[VersionBrief] = None
    status: RequirementStatus
    created_by: str
    created_at: datetime
    updated_at: datetime


class RequirementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    external_url: Optional[str] = Field(default=None, max_length=1024)
    version_id: Optional[str] = None
    status: RequirementStatus = RequirementStatus.not_tested


class RequirementUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=512)
    external_url: Optional[str] = Field(default=None, max_length=1024)
    version_id: Optional[str] = None
    status: Optional[RequirementStatus] = None
