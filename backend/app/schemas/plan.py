from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.plan import ExecuteResult, PlanStatus
from app.schemas.case import TestCaseOut
from app.schemas.common import ORMBase
from app.schemas.version import VersionBrief


class TestPlanOut(ORMBase):
    id: str
    project_id: str
    name: str
    status: PlanStatus
    version_id: Optional[str] = None
    version: Optional[VersionBrief] = None
    owner_id: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


class TestPlanListItemOut(TestPlanOut):
    case_total: int = 0
    pass_count: int = 0
    fail_count: int = 0
    block_count: int = 0
    skip_count: int = 0
    not_run_count: int = 0
    pass_rate: float = 0.0


class TestPlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    status: PlanStatus = PlanStatus.draft
    description: Optional[str] = None
    version_id: Optional[str] = None


class TestPlanUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[PlanStatus] = None
    description: Optional[str] = None
    owner_id: Optional[str] = None
    version_id: Optional[str] = None


class PlanCaseOut(ORMBase):
    id: str
    plan_id: str
    case_id: str
    sort: int
    case: Optional[TestCaseOut] = None
    result: Optional["PlanCaseResultOut"] = None


class PlanCaseResultOut(ORMBase):
    id: str
    plan_case_id: str
    executor_id: Optional[str]
    result: ExecuteResult
    comment: Optional[str]
    executed_at: Optional[datetime]


class PlanCaseAdd(BaseModel):
    case_ids: list[str]


class PlanCaseResultUpdate(BaseModel):
    plan_case_id: str
    result: ExecuteResult
    comment: Optional[str] = None


class PlanStatsOut(BaseModel):
    total: int
    not_run: int
    pass_count: int
    fail_count: int
    block_count: int
    skip_count: int
    pass_rate: float
