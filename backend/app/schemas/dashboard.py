from typing import Optional

from pydantic import BaseModel

from app.models.requirement import RequirementStatus
from app.schemas.bug import BugOut
from app.schemas.version import VersionBrief


class DashboardSummary(BaseModel):
    version_count: int
    requirement_count: int
    case_count: int
    bug_count: int


class ActivePlanBrief(BaseModel):
    id: str
    name: str
    status: str
    case_total: int
    not_run: int
    pass_rate: Optional[float] = None


class StatusCountItem(BaseModel):
    key: str
    label: str
    count: int


class StatusBreakdown(BaseModel):
    total: int
    by_status: list[StatusCountItem]


class BugOverviewCell(BaseModel):
    status_key: str
    version_id: Optional[str] = None
    count: int


class BugOverviewChart(BaseModel):
    """全项目缺陷：横轴为状态，柱内按规划版本堆叠。"""

    total: int
    by_status: list[StatusCountItem]
    versions: list[VersionBrief] = []
    cells: list[BugOverviewCell] = []


class VersionFocus(BaseModel):
    version: Optional[VersionBrief] = None
    versions: list[VersionBrief] = []
    requirements: StatusBreakdown
    bugs: StatusBreakdown
    plans: StatusBreakdown


class PlanChartPoint(BaseModel):
    plan_id: str
    plan_name: str
    status: str
    by_result: list[StatusCountItem]
    pass_rate: Optional[float] = None


class PlanExecutionChart(BaseModel):
    points: list[PlanChartPoint]


class DashboardOverview(BaseModel):
    version_focus: VersionFocus
    bug_overview_chart: BugOverviewChart
    plan_execution_chart: PlanExecutionChart


class RequirementTodoBrief(BaseModel):
    id: str
    num: int
    title: str
    status: RequirementStatus
    version: Optional[VersionBrief] = None


class DashboardTodo(BaseModel):
    draft_plans: list[ActivePlanBrief] = []
    active_plans_todo: list[ActivePlanBrief] = []
    fixed_bugs: list[BugOut] = []
    not_tested_requirements: list[RequirementTodoBrief] = []
    testing_requirements: list[RequirementTodoBrief] = []
    follower_todo_bugs: list[BugOut] = []


class DashboardWorkbench(BaseModel):
    summary: DashboardSummary
    overview: DashboardOverview
    todo: DashboardTodo
    project_role: str
