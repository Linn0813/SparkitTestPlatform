from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase
from app.schemas.user import UserOut
from app.schemas.version import VersionBrief


class BugOut(ORMBase):
    id: str
    project_id: str
    num: int
    title: str
    status_key: str
    assignee_id: Optional[str]
    reporter_id: str
    description: Optional[str]
    custom_fields: dict[str, Any]
    requirement_ids: list[str] = []
    plan_ids: list[str] = []
    plan_version_id: Optional[str] = None
    found_version_id: Optional[str] = None
    plan_version: Optional[VersionBrief] = None
    found_version: Optional[VersionBrief] = None
    follower_ids: list[str] = []
    created_at: datetime
    updated_at: datetime
    assignee: Optional[UserOut] = None
    reporter: Optional[UserOut] = None
    followers: list[UserOut] = []


class BugListPageOut(BaseModel):
    items: list[BugOut]
    total: int
    page: int
    page_size: int


class BugCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    status_key: Optional[str] = None
    assignee_id: Optional[str] = None
    description: Optional[str] = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    case_ids: list[str] = Field(default_factory=list)
    requirement_ids: list[str] = Field(default_factory=list)
    plan_ids: list[str] = Field(default_factory=list)
    plan_version_id: Optional[str] = None
    found_version_id: Optional[str] = None
    reporter_id: Optional[str] = None
    follower_ids: list[str] = Field(default_factory=list)


class BugUpdate(BaseModel):
    title: Optional[str] = None
    status_key: Optional[str] = None
    assignee_id: Optional[str] = None
    description: Optional[str] = None
    custom_fields: Optional[dict[str, Any]] = None
    requirement_ids: Optional[list[str]] = None
    plan_ids: Optional[list[str]] = None
    plan_version_id: Optional[str] = None
    found_version_id: Optional[str] = None
    reporter_id: Optional[str] = None
    follower_ids: Optional[list[str]] = None


class BugAttachmentOut(ORMBase):
    id: str
    bug_id: str
    object_key: str
    filename: str
    size: int
    created_at: datetime


class BugCaseLinkOut(BaseModel):
    id: str
    bug_id: str
    case_id: str

    model_config = {"from_attributes": True}


class BugCommentCreate(BaseModel):
    body: str = Field(min_length=1)


class BugCommentOut(ORMBase):
    id: str
    bug_id: str
    user_id: str
    body: str
    created_at: datetime
    user: Optional[UserOut] = None


class BugImportErrorOut(BaseModel):
    row: int
    message: str


class BugImportResultOut(BaseModel):
    created: int
    errors: list[BugImportErrorOut] = Field(default_factory=list)


class BugActivityOut(BaseModel):
    id: str
    source: str
    action_type: str
    summary: str
    detail: dict[str, Any]
    actor: Optional[UserOut] = None
    created_at: datetime
