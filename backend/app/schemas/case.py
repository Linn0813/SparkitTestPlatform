from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.case import CasePriority
from app.schemas.common import ORMBase


class CaseModuleOut(ORMBase):
    id: str
    project_id: str
    parent_id: Optional[str]
    name: str
    sort: int
    created_at: datetime


class CaseModuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    parent_id: Optional[str] = None
    sort: int = 0


class CaseModuleUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[str] = None
    sort: Optional[int] = None


class TestCaseOut(ORMBase):
    id: str
    project_id: str
    module_id: str
    module_path: Optional[str] = None
    title: str
    priority: CasePriority
    precondition: Optional[str]
    step_text: Optional[str]
    expected_result: Optional[str]
    steps: list[dict[str, Any]]
    tags: list[str]
    custom_fields: dict[str, Any]
    requirement_ids: list[str] = []
    created_by: str
    created_at: datetime
    updated_at: datetime


class TestCaseCreate(BaseModel):
    module_id: str
    title: str = Field(min_length=1, max_length=512)
    priority: CasePriority = CasePriority.P2
    precondition: Optional[str] = None
    step_text: Optional[str] = None
    expected_result: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    requirement_ids: list[str] = Field(default_factory=list)


class CaseImportErrorOut(BaseModel):
    row: int
    message: str


class CaseImportResultOut(BaseModel):
    created: int
    errors: list[CaseImportErrorOut] = Field(default_factory=list)


class TestCaseUpdate(BaseModel):
    module_id: Optional[str] = None
    title: Optional[str] = None
    priority: Optional[CasePriority] = None
    precondition: Optional[str] = None
    step_text: Optional[str] = None
    expected_result: Optional[str] = None
    tags: Optional[list[str]] = None
    custom_fields: Optional[dict[str, Any]] = None
    requirement_ids: Optional[list[str]] = None
