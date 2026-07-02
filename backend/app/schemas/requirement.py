from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from app.models.requirement import RequirementNodeState, RequirementStatus
from app.schemas.common import ORMBase
from app.schemas.user import UserOut
from app.schemas.version import VersionBrief


class RequirementNodeTaskOut(BaseModel):
    id: str
    requirement_id: str
    node_key: str
    title: str
    role_key: str
    assignee_id: Optional[str] = None
    assignee: Optional[UserOut] = None
    estimate_points: Optional[float] = None
    scheduled_start: Optional[date] = None
    scheduled_end: Optional[date] = None
    sort: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RequirementNodeTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    role_key: str = Field(min_length=1, max_length=64)
    assignee_id: Optional[str] = None
    estimate_points: Optional[float] = Field(default=None, ge=0)
    scheduled_start: Optional[date] = None
    scheduled_end: Optional[date] = None


class RequirementNodeTaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=256)
    role_key: Optional[str] = Field(default=None, min_length=1, max_length=64)
    assignee_id: Optional[str] = None
    estimate_points: Optional[float] = Field(default=None, ge=0)
    scheduled_start: Optional[date] = None
    scheduled_end: Optional[date] = None
    sort: Optional[int] = Field(default=None, ge=0)


class RequirementNodeProgressOut(BaseModel):
    node_key: str
    label: str
    state: RequirementNodeState
    role_keys: list[str]
    enabled: bool = True
    lane_index: int = 0
    lane_indexes: list[int] = Field(default_factory=list)
    blocks_lane_gate: bool = True
    sort_in_lane: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    operator_id: Optional[str] = None
    planned_schedule_start: Optional[date] = None
    planned_schedule_end: Optional[date] = None


class RequirementWorkflowNodeDefOut(BaseModel):
    id: str
    project_id: str
    node_key: str
    label: str
    role_keys: list[str]
    lane_index: int
    lane_indexes: list[int]
    blocks_lane_gate: bool = True
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
                "node_key": data.node_key,
                "label": data.label,
                "role_keys": data.role_keys,
                "lane_index": indexes[0],
                "lane_indexes": indexes,
                "blocks_lane_gate": bool(getattr(data, "blocks_lane_gate", True)),
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


class RequirementWorkflowNodeDefCreate(BaseModel):
    label: str = Field(min_length=1, max_length=128)
    role_keys: list[str] = Field(default_factory=list)
    lane_indexes: list[int] = Field(min_length=1)
    blocks_lane_gate: bool = True
    sort_in_lane: int = Field(ge=0, default=0)


class RequirementWorkflowNodeDefUpdate(BaseModel):
    label: Optional[str] = Field(default=None, min_length=1, max_length=128)
    role_keys: Optional[list[str]] = None
    lane_indexes: Optional[list[int]] = Field(default=None, min_length=1)
    blocks_lane_gate: Optional[bool] = None
    sort_in_lane: Optional[int] = Field(default=None, ge=0)


class RequirementWorkflowNodeReorderItem(BaseModel):
    id: str
    lane_index: int = Field(ge=0)
    sort_in_lane: int = Field(ge=0, default=0)


class RequirementWorkflowNodeReorderBody(BaseModel):
    items: list[RequirementWorkflowNodeReorderItem]


class RequirementStatusRuleOut(BaseModel):
    id: str
    project_id: str
    status: str
    node_keys: list[str]
    sort: int
    trigger_type: str = "lane"

    model_config = {"from_attributes": True}


class RequirementStatusRuleItem(BaseModel):
    status: str = Field(min_length=1, max_length=32)
    node_keys: list[str] = Field(default_factory=list)
    sort: int = Field(ge=0, default=0)
    trigger_type: str = Field(default="lane", max_length=32)


class RequirementStatusRulesReplaceBody(BaseModel):
    rules: list[RequirementStatusRuleItem]


class RequirementStatusSyncBatchOut(BaseModel):
    updated_count: int


class RequirementWorkflowOut(BaseModel):
    defs: list[RequirementWorkflowNodeDefOut]
    nodes: list[RequirementNodeProgressOut]


class RequirementWorkflowEnabledUpdate(BaseModel):
    enabled: dict[str, bool]
    expected_updated_at: Optional[datetime] = None


class RequirementOut(ORMBase):
    id: str
    project_id: str
    num: int
    title: str
    external_url: Optional[str]
    version_id: Optional[str] = None
    version: Optional[VersionBrief] = None
    priority: str
    req_type: str
    status: RequirementStatus
    frontend_rd_id: Optional[str] = None
    backend_rd_id: Optional[str] = None
    pm_id: Optional[str] = None
    tech_owner_id: Optional[str] = None
    qa_id: Optional[str] = None
    designer_id: Optional[str] = None
    role_assignee_ids: dict[str, list[str]] = Field(default_factory=dict)
    selected_role_keys: list[str] = Field(default_factory=list)
    custom_fields: dict = Field(default_factory=dict)
    frontend_rd: Optional[UserOut] = None
    backend_rd: Optional[UserOut] = None
    pm: Optional[UserOut] = None
    tech_owner: Optional[UserOut] = None
    qa: Optional[UserOut] = None
    designer: Optional[UserOut] = None
    nodes: list[RequirementNodeProgressOut] = Field(default_factory=list)
    node_tasks: list[RequirementNodeTaskOut] = Field(default_factory=list)
    dev_handoff_date: Optional[date] = None
    estimated_completion_date: Optional[date] = None  # 预计完成：测试节点最晚结束日期，无则降级到开发节点
    developers: list[UserOut] = Field(default_factory=list)
    created_by: str
    created_at: datetime
    updated_at: datetime


class RequirementListPageOut(BaseModel):
    items: list[RequirementOut]
    total: int
    page: int
    page_size: int


class RequirementSelectOptionOut(BaseModel):
    """下拉/筛选器用轻量选项，避免拉取完整 RequirementOut。"""

    id: str
    num: int
    title: str
    status: RequirementStatus
    external_url: Optional[str] = None

    model_config = {"from_attributes": True}


class RequirementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    external_url: Optional[str] = Field(default=None, max_length=1024)
    version_id: Optional[str] = None
    priority: str = "p1"
    req_type: str = "feature"
    frontend_rd_id: Optional[str] = None
    backend_rd_id: Optional[str] = None
    pm_id: Optional[str] = None
    tech_owner_id: Optional[str] = None
    qa_id: Optional[str] = None
    designer_id: Optional[str] = None
    role_assignee_ids: Optional[dict[str, list[str]]] = None
    selected_role_keys: Optional[list[str]] = None
    enabled: Optional[dict[str, bool]] = None
    custom_fields: dict = Field(default_factory=dict)


class RequirementUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=512)
    external_url: Optional[str] = Field(default=None, max_length=1024)
    version_id: Optional[str] = None
    priority: Optional[str] = None
    req_type: Optional[str] = None
    frontend_rd_id: Optional[str] = None
    backend_rd_id: Optional[str] = None
    pm_id: Optional[str] = None
    tech_owner_id: Optional[str] = None
    qa_id: Optional[str] = None
    designer_id: Optional[str] = None
    role_assignee_ids: Optional[dict[str, list[str]]] = None
    selected_role_keys: Optional[list[str]] = None
    custom_fields: Optional[dict] = None
    expected_updated_at: Optional[datetime] = None


class RequirementNodeActionBody(BaseModel):
    action: Literal["start", "complete", "skip", "reopen", "reject"]


class RequirementActivityOut(BaseModel):
    id: str
    action_type: str
    summary: str
    detail: dict
    actor: Optional[UserOut] = None
    created_at: datetime


class RequirementCommentCreate(BaseModel):
    body: str = Field(min_length=1)


class RequirementCommentOut(ORMBase):
    id: str
    requirement_id: str
    user_id: str
    body: str
    created_at: datetime
    user: Optional[UserOut] = None
