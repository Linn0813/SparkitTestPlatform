from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# 通用
# ---------------------------------------------------------------------------

class VersionBriefOut(BaseModel):
    id: str
    num: int
    name: str


# ---------------------------------------------------------------------------
# 1. 需求 Bug 密度
# ---------------------------------------------------------------------------

class RequirementBugDensityItem(BaseModel):
    requirement_id: str
    requirement_num: int
    title: str
    priority: str
    bug_count: int
    estimate_points: float
    density: Optional[float]  # None 表示 estimate_points 为 0


# ---------------------------------------------------------------------------
# 2. 高优需求停滞预警
# ---------------------------------------------------------------------------

class StaleRequirementItem(BaseModel):
    requirement_id: str
    requirement_num: int
    title: str
    priority: str
    status: str
    stale_days: int
    warning_level: str  # "warning" | "danger"
    frontend_rd_name: Optional[str]
    backend_rd_name: Optional[str]
    qa_name: Optional[str]


# ---------------------------------------------------------------------------
# 3. 需求交付健康度（按版本）
# ---------------------------------------------------------------------------

class VersionDeliveryHealth(BaseModel):
    version_id: str
    version_name: str
    version_status: str
    total_requirements: int
    completed_requirements: int
    incomplete_requirements: int
    completion_rate: float
    at_risk: bool  # 版本已发布但仍有未完成需求


# ---------------------------------------------------------------------------
# 4. 漏测率
# ---------------------------------------------------------------------------

class LeakageRateOut(BaseModel):
    total_bugs: int
    online_bugs: int
    leakage_rate: float  # 百分比 0~100
    # 按版本趋势
    by_version: list[dict[str, Any]]  # [{version_name, total, online, rate}]


# ---------------------------------------------------------------------------
# 5. Bug 修复反弹率
# ---------------------------------------------------------------------------

class BugReflowRateOut(BaseModel):
    resolved_bugs: int
    reflowed_bugs: int
    reflow_rate: float  # 百分比
    reflow_bug_list: list[dict[str, Any]]  # [{bug_num, title, reflow_count, assignee_name}]


# ---------------------------------------------------------------------------
# 6. 研发人员 Bug 引入率
# ---------------------------------------------------------------------------

class DeveloperBugRateItem(BaseModel):
    user_id: str
    user_name: str
    requirement_count: int
    bug_count: int
    estimate_points: float
    bug_rate: Optional[float]  # None 表示 estimate_points 为 0


# ---------------------------------------------------------------------------
# 7. P0/P1 Bug 响应时效
# ---------------------------------------------------------------------------

class BugResponseTimeItem(BaseModel):
    bug_id: str
    bug_num: int
    title: str
    severity: str
    created_at: str
    first_response_hours: Optional[float]  # None 表示尚未处理
    warning_level: str  # "ok" | "warning" | "danger" | "unhandled"
    assignee_name: Optional[str]


class BugResponseTimeOut(BaseModel):
    avg_response_hours: Optional[float]
    items: list[BugResponseTimeItem]


# ---------------------------------------------------------------------------
# 8. Bug 来源分布趋势
# ---------------------------------------------------------------------------

class BugSourceTrendItem(BaseModel):
    label: str  # 版本名或月份
    online: int       # 线上反馈
    internal: int     # 内部体验
    testing: int      # 需求测试
    other: int        # 其他


# ---------------------------------------------------------------------------
# 完整响应
# ---------------------------------------------------------------------------

class QualityDashboardOut(BaseModel):
    versions: list[VersionBriefOut]  # 可用版本列表（用于筛选器）

    # 需求质量
    requirement_bug_density: list[RequirementBugDensityItem]
    stale_requirements: list[StaleRequirementItem]
    version_delivery_health: list[VersionDeliveryHealth]

    # 缺陷质量
    leakage_rate: LeakageRateOut
    reflow_rate: BugReflowRateOut
    developer_bug_rate: list[DeveloperBugRateItem]
    bug_response_time: BugResponseTimeOut
    bug_source_trend: list[BugSourceTrendItem]
