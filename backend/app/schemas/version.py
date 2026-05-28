from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase

VersionStatusLiteral = Literal["planning", "developing", "releasing", "reviewing", "ended"]
VersionNodeStateLiteral = Literal["pending", "completed"]
VersionNodeKeyLiteral = Literal[
    "planning",
    "development",
    "release_verification",
    "gp_review",
    "as_review",
    "website_link",
    "live",
]


class VersionBrief(ORMBase):
    id: str
    num: int
    name: str
    released_at: Optional[date] = None
    status: VersionStatusLiteral = "planning"


class VersionNodeProgressOut(BaseModel):
    node_key: VersionNodeKeyLiteral
    state: VersionNodeStateLiteral
    completed_at: Optional[datetime] = None
    operator_id: Optional[str] = None

    model_config = {"from_attributes": True}


class ProjectVersionOut(ORMBase):
    id: str
    project_id: str
    num: int
    name: str
    status: VersionStatusLiteral
    released_at: Optional[date] = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    nodes: list[VersionNodeProgressOut] = Field(default_factory=list)


class ProjectVersionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    released_at: Optional[date] = None


class ProjectVersionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    released_at: Optional[date] = None


class VersionNodeCompleteOut(BaseModel):
    version: ProjectVersionOut
    wecom_mention_count: Optional[int] = None
