from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMBase

VersionStatusLiteral = Literal["planning", "developing", "releasing", "reviewing", "ended"]
VersionNodeStateLiteral = Literal["pending", "completed"]
VersionTypeLiteral = Literal["app_release", "hotfix"]


class VersionBrief(ORMBase):
    id: str
    num: int
    name: str
    released_at: Optional[date] = None
    status: VersionStatusLiteral = "planning"
    version_type: VersionTypeLiteral = "app_release"


class VersionWorkflowNodeDefOut(BaseModel):
    id: str
    project_id: str
    version_type: VersionTypeLiteral
    node_key: str
    label: str
    lane_index: int
    lane_indexes: list[int]
    sort_in_lane: int

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def normalize_lane_indexes(cls, data: object) -> object:
        if not isinstance(data, dict):
            lane_indexes = getattr(data, "lane_indexes", None)
            lane_index = getattr(data, "lane_index", 0)
            if lane_indexes:
                indexes = sorted(set(int(i) for i in lane_indexes))
            else:
                indexes = [int(lane_index)]
            return {
                "id": data.id,
                "project_id": data.project_id,
                "version_type": data.version_type,
                "node_key": data.node_key,
                "label": data.label,
                "lane_index": indexes[0],
                "lane_indexes": indexes,
                "sort_in_lane": data.sort_in_lane,
            }
        lane_indexes = data.get("lane_indexes")
        lane_index = data.get("lane_index", 0)
        if lane_indexes:
            indexes = sorted(set(int(i) for i in lane_indexes))
        else:
            indexes = [int(lane_index)]
        data = dict(data)
        data["lane_indexes"] = indexes
        data["lane_index"] = indexes[0]
        return data


class VersionWorkflowNodeDefCreate(BaseModel):
    node_key: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)
    lane_indexes: list[int] = Field(min_length=1)
    sort_in_lane: int = Field(ge=0, default=0)


class VersionWorkflowNodeDefUpdate(BaseModel):
    label: Optional[str] = Field(default=None, min_length=1, max_length=128)
    lane_indexes: Optional[list[int]] = Field(default=None, min_length=1)
    sort_in_lane: Optional[int] = Field(default=None, ge=0)


class VersionWorkflowNodeReorderItem(BaseModel):
    id: str
    lane_index: int = Field(ge=0)
    sort_in_lane: int = Field(ge=0, default=0)


class VersionWorkflowNodeReorderBody(BaseModel):
    items: list[VersionWorkflowNodeReorderItem]


class VersionNodeProgressOut(BaseModel):
    node_key: str
    state: VersionNodeStateLiteral
    completed_at: Optional[datetime] = None
    operator_id: Optional[str] = None
    assignee_id: Optional[str] = None
    scheduled_start: Optional[date] = None
    scheduled_end: Optional[date] = None

    model_config = {"from_attributes": True}


class VersionNodeUpdate(BaseModel):
    assignee_id: Optional[str] = None
    scheduled_start: Optional[date] = None
    scheduled_end: Optional[date] = None


class ProjectVersionOut(ORMBase):
    id: str
    project_id: str
    num: int
    name: str
    version_type: VersionTypeLiteral
    status: VersionStatusLiteral
    released_at: Optional[date] = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    nodes: list[VersionNodeProgressOut] = Field(default_factory=list)
    workflow_defs: list[VersionWorkflowNodeDefOut] = Field(default_factory=list)


class ProjectVersionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    released_at: Optional[date] = None
    version_type: VersionTypeLiteral = "app_release"


class ProjectVersionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    released_at: Optional[date] = None
    version_type: Optional[VersionTypeLiteral] = None


class VersionNodeCompleteOut(BaseModel):
    version: ProjectVersionOut
    wecom_mention_count: Optional[int] = None
