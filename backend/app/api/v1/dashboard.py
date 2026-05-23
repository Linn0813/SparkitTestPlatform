from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory

from app.constants.requirement_status import (
    REQUIREMENT_STATUS_KEYS,
    REQUIREMENT_STATUS_LABELS,
)
from app.services.dashboard_version import pick_default_version
from app.services.serializers import bug_out_todo
from app.constants.dashboard_todo import (
    BUG_OVERVIEW_EXCLUDED_STATUS_KEYS,
    MEMBER_FOLLOWER_TODO_STATUS_KEYS,
    TESTER_FIXED_BUG_STATUS_KEY,
    TESTER_TODO_REQUIREMENT_STATUS_KEYS,
)
from app.core.database import get_db
from app.core.deps import ProjectContext, require_project_context
from app.core.project_permissions import get_project_role
from app.models.bug import Bug, BugFollowerLink
from app.models.case import TestCase
from app.models.plan import ExecuteResult, PlanCase, PlanCaseResult, PlanStatus, TestPlan
from app.models.project import ProjectRole
from app.models.project_version import ProjectVersion
from app.models.requirement import Requirement, RequirementStatus
from app.models.template import BugStatus
from app.models.user import User
from app.schemas.bug import BugOut
from app.schemas.dashboard import (
    ActivePlanBrief,
    BugFocus,
    BugFollowerCell,
    BugFollowerOverviewChart,
    BugOverviewCell,
    BugOverviewChart,
    DashboardOverview,
    DashboardSummary,
    DashboardTodo,
    DashboardWorkbench,
    FollowerBrief,
    PlanChartPoint,
    PlanExecutionChart,
    PlanFocus,
    RequirementTodoBrief,
    StatusBreakdown,
    StatusCountItem,
    VersionFocus,
)
from app.schemas.version import VersionBrief

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_TODO_LIST_LIMIT = 10
_VERSION_PICKER_LIMIT = 30
_PLAN_CHART_LIMIT = 8

_PLAN_STATUS_LABELS = {
    PlanStatus.draft: "未开始",
    PlanStatus.active: "进行中",
    PlanStatus.archived: "已结束",
}

_EXECUTE_RESULT_LABELS = {
    ExecuteResult.not_run: "未执行",
    ExecuteResult.pass_: "通过",
    ExecuteResult.fail: "失败",
    ExecuteResult.block: "阻塞",
    ExecuteResult.skip: "跳过",
}


async def _bug_status_legend(db: AsyncSession, project_id: str) -> list[StatusCountItem]:
    rows = await db.execute(
        select(BugStatus.key, BugStatus.label)
        .where(BugStatus.project_id == project_id)
        .order_by(BugStatus.sort)
    )
    return [StatusCountItem(key=k, label=lbl, count=0) for k, lbl in rows.all()]


def _version_brief(ver: ProjectVersion) -> VersionBrief:
    return VersionBrief(id=ver.id, num=ver.num, name=ver.name)


def _version_picker_order():
    return (
        ProjectVersion.released_at.is_(None),
        ProjectVersion.released_at.desc(),
        ProjectVersion.num.desc(),
    )


async def _resolve_version(
    db: AsyncSession, project_id: str, version_id: Optional[str]
) -> ProjectVersion | None:
    if version_id:
        ver = await db.get(ProjectVersion, version_id)
        if not ver or ver.project_id != project_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid version")
        return ver
    result = await db.execute(select(ProjectVersion).where(ProjectVersion.project_id == project_id))
    versions = list(result.scalars().all())
    return pick_default_version(versions)


async def _version_focus(
    db: AsyncSession, project_id: str, version_id: Optional[str]
) -> VersionFocus:
    ver = await _resolve_version(db, project_id, version_id)
    versions_q = await db.execute(
        select(ProjectVersion)
        .where(ProjectVersion.project_id == project_id)
        .order_by(*_version_picker_order())
        .limit(_VERSION_PICKER_LIMIT)
    )
    versions = [_version_brief(v) for v in versions_q.scalars().all()]

    if not ver:
        empty = StatusBreakdown(total=0, by_status=[])
        return VersionFocus(
            version=None,
            versions=versions,
            requirements=empty,
            bugs=empty,
            plans=empty,
        )

    vid = ver.id
    req_labels = dict(REQUIREMENT_STATUS_LABELS)
    req_keys = REQUIREMENT_STATUS_KEYS
    req_rows = await db.execute(
        select(Requirement.status, func.count())
        .where(Requirement.project_id == project_id, Requirement.version_id == vid)
        .group_by(Requirement.status)
    )
    req_count_map: dict[str, int] = {}
    for st, cnt in req_rows.all():
        key = st.value if hasattr(st, "value") else str(st)
        req_count_map[key] = cnt
    req_by_status = [
        StatusCountItem(key=k, label=req_labels[k], count=req_count_map.get(k, 0)) for k in req_keys
    ]
    requirements = StatusBreakdown(
        total=sum(s.count for s in req_by_status),
        by_status=req_by_status,
    )

    legend = await _bug_status_legend(db, project_id)
    legend_keys = [s.key for s in legend]
    label_map = {s.key: s.label for s in legend}
    bug_rows = await db.execute(
        select(Bug.status_key, func.count())
        .where(Bug.project_id == project_id, Bug.plan_version_id == vid)
        .group_by(Bug.status_key)
    )
    bug_count_map = {k: c for k, c in bug_rows.all()}
    bug_by_status = [
        StatusCountItem(key=k, label=label_map.get(k, k), count=bug_count_map.get(k, 0))
        for k in legend_keys
    ]
    for key, cnt in bug_count_map.items():
        if key not in legend_keys and cnt > 0:
            bug_by_status.append(StatusCountItem(key=key, label=label_map.get(key, key), count=cnt))
    bugs = StatusBreakdown(total=sum(s.count for s in bug_by_status), by_status=bug_by_status)

    plan_keys = ("draft", "active", "archived")
    plan_labels = {k.value if hasattr(k, "value") else str(k): v for k, v in _PLAN_STATUS_LABELS.items()}
    plan_rows = await db.execute(
        select(TestPlan.status, func.count())
        .where(TestPlan.project_id == project_id, TestPlan.version_id == vid)
        .group_by(TestPlan.status)
    )
    plan_count_map: dict[str, int] = {}
    for st, cnt in plan_rows.all():
        key = st.value if hasattr(st, "value") else str(st)
        plan_count_map[key] = cnt
    plan_by_status = [
        StatusCountItem(key=k, label=plan_labels.get(k, k), count=plan_count_map.get(k, 0))
        for k in plan_keys
    ]
    plans = StatusBreakdown(total=sum(s.count for s in plan_by_status), by_status=plan_by_status)

    return VersionFocus(
        version=_version_brief(ver),
        versions=versions,
        requirements=requirements,
        bugs=bugs,
        plans=plans,
    )


async def _bug_overview_chart(db: AsyncSession, project_id: str) -> BugOverviewChart:
    """全项目缺陷：按状态分组，柱内按规划版本堆叠；排除已验收、已拒绝、转需求。"""
    excluded = set(BUG_OVERVIEW_EXCLUDED_STATUS_KEYS)
    legend = await _bug_status_legend(db, project_id)
    active_legend = [s for s in legend if s.key not in excluded]
    legend_keys = [s.key for s in active_legend]
    label_map = {s.key: s.label for s in active_legend}

    matrix_rows = await db.execute(
        select(Bug.status_key, Bug.plan_version_id, func.count())
        .where(Bug.project_id == project_id, Bug.status_key.notin_(tuple(excluded)))
        .group_by(Bug.status_key, Bug.plan_version_id)
    )
    cell_map: dict[tuple[str, str | None], int] = {}
    status_totals: dict[str, int] = {}
    version_ids: set[str] = set()
    for status_key, plan_version_id, cnt in matrix_rows.all():
        cell_map[(status_key, plan_version_id)] = cnt
        status_totals[status_key] = status_totals.get(status_key, 0) + cnt
        if plan_version_id:
            version_ids.add(plan_version_id)

    by_status: list[StatusCountItem] = [
        StatusCountItem(key=k, label=label_map.get(k, k), count=status_totals.get(k, 0))
        for k in legend_keys
    ]
    for key, cnt in status_totals.items():
        if key not in legend_keys and cnt > 0:
            by_status.append(StatusCountItem(key=key, label=label_map.get(key, key), count=cnt))

    versions: list[VersionBrief] = []
    if version_ids:
        ver_rows = await db.execute(
            select(ProjectVersion)
            .where(ProjectVersion.id.in_(version_ids), ProjectVersion.project_id == project_id)
            .order_by(ProjectVersion.updated_at.desc())
        )
        versions = [_version_brief(v) for v in ver_rows.scalars().all()]

    cells: list[BugOverviewCell] = []
    for (status_key, version_id), cnt in cell_map.items():
        if cnt > 0:
            cells.append(BugOverviewCell(status_key=status_key, version_id=version_id, count=cnt))

    total = sum(s.count for s in by_status)
    return BugOverviewChart(total=total, by_status=by_status, versions=versions, cells=cells)


async def _bug_follower_overview_chart(db: AsyncSession, project_id: str) -> BugFollowerOverviewChart:
    """跟进人待办（待确认/处理中/挂起）× 规划版本。"""
    status_keys = MEMBER_FOLLOWER_TODO_STATUS_KEYS
    cell_map: dict[tuple[str | None, str | None], int] = defaultdict(int)
    follower_ids: set[str] = set()
    version_ids: set[str] = set()

    linked_rows = await db.execute(
        select(BugFollowerLink.user_id, Bug.plan_version_id, func.count())
        .join(Bug, Bug.id == BugFollowerLink.bug_id)
        .where(Bug.project_id == project_id, Bug.status_key.in_(status_keys))
        .group_by(BugFollowerLink.user_id, Bug.plan_version_id)
    )
    for user_id, plan_version_id, cnt in linked_rows.all():
        cell_map[(user_id, plan_version_id)] = cnt
        follower_ids.add(user_id)
        if plan_version_id:
            version_ids.add(plan_version_id)

    has_follower_subq = select(BugFollowerLink.bug_id).distinct()
    unassigned_rows = await db.execute(
        select(Bug.plan_version_id, func.count())
        .where(
            Bug.project_id == project_id,
            Bug.status_key.in_(status_keys),
            Bug.id.notin_(has_follower_subq),
        )
        .group_by(Bug.plan_version_id)
    )
    for plan_version_id, cnt in unassigned_rows.all():
        if cnt > 0:
            cell_map[(None, plan_version_id)] = cnt
            if plan_version_id:
                version_ids.add(plan_version_id)

    followers: list[FollowerBrief] = []
    if any(fid is None for fid, _ in cell_map):
        followers.append(FollowerBrief(id=None, label="未指定跟进人"))
    if follower_ids:
        user_rows = await db.execute(select(User.id, User.name).where(User.id.in_(follower_ids)))
        name_map = {uid: name for uid, name in user_rows.all()}
        for uid in sorted(follower_ids, key=lambda x: name_map.get(x, x)):
            followers.append(FollowerBrief(id=uid, label=name_map.get(uid, uid)))

    follower_totals: dict[str | None, int] = defaultdict(int)
    for (fid, _), cnt in cell_map.items():
        follower_totals[fid] += cnt
    followers.sort(key=lambda f: (-follower_totals.get(f.id, 0), f.label))

    versions: list[VersionBrief] = []
    if version_ids:
        ver_rows = await db.execute(
            select(ProjectVersion)
            .where(ProjectVersion.id.in_(version_ids), ProjectVersion.project_id == project_id)
            .order_by(*_version_picker_order())
        )
        versions = [_version_brief(v) for v in ver_rows.scalars().all()]

    cells = [
        BugFollowerCell(follower_id=fid, version_id=vid, count=cnt)
        for (fid, vid), cnt in cell_map.items()
        if cnt > 0
    ]
    return BugFollowerOverviewChart(followers=followers, versions=versions, cells=cells)


async def _bug_focus(db: AsyncSession, project_id: str) -> BugFocus:
    by_version_status = await _bug_overview_chart(db, project_id)
    follower_by_version = await _bug_follower_overview_chart(db, project_id)
    return BugFocus(
        by_version_status=by_version_status,
        follower_by_version=follower_by_version,
    )


async def _plan_case_results_by_pc_id(db: AsyncSession, plan_id: str) -> tuple[list[str], dict[str, ExecuteResult]]:
    plan_map = await _plan_case_results_map(db, [plan_id])
    return plan_map.get(plan_id, ([], {}))


async def _plan_case_results_map(
    db: AsyncSession, plan_ids: list[str]
) -> dict[str, tuple[list[str], dict[str, ExecuteResult]]]:
    if not plan_ids:
        return {}
    pc_rows = await db.execute(
        select(PlanCase.plan_id, PlanCase.id).where(PlanCase.plan_id.in_(plan_ids))
    )
    pcs_by_plan: dict[str, list[str]] = defaultdict(list)
    all_pc_ids: list[str] = []
    for plan_id, pc_id in pc_rows.all():
        pcs_by_plan[plan_id].append(pc_id)
        all_pc_ids.append(pc_id)
    result_by_pc: dict[str, ExecuteResult] = {}
    if all_pc_ids:
        res_rows = await db.execute(
            select(PlanCaseResult.plan_case_id, PlanCaseResult.result).where(
                PlanCaseResult.plan_case_id.in_(all_pc_ids)
            )
        )
        result_by_pc = dict(res_rows.all())
    out: dict[str, tuple[list[str], dict[str, ExecuteResult]]] = {}
    for plan_id in plan_ids:
        pc_ids = pcs_by_plan.get(plan_id, [])
        out[plan_id] = (pc_ids, {pc: result_by_pc.get(pc, ExecuteResult.not_run) for pc in pc_ids})
    return out


def _execute_result_counts(
    pc_ids: list[str], result_by_pc: dict[str, ExecuteResult]
) -> tuple[list[StatusCountItem], float | None]:
    counter = {r: 0 for r in ExecuteResult}
    pass_count = 0
    executed = 0
    for pc_id in pc_ids:
        key = result_by_pc.get(pc_id, ExecuteResult.not_run)
        counter[key] = counter.get(key, 0) + 1
        if key != ExecuteResult.not_run:
            executed += 1
            if key == ExecuteResult.pass_:
                pass_count += 1
    items: list[StatusCountItem] = []
    for result in ExecuteResult:
        key = result.value if hasattr(result, "value") else str(result)
        items.append(
            StatusCountItem(
                key=key,
                label=_EXECUTE_RESULT_LABELS.get(result, key),
                count=counter.get(result, 0),
            )
        )
    pass_rate = round(pass_count / executed * 100, 1) if executed else None
    return items, pass_rate


async def _plan_progress_map(
    db: AsyncSession, plan_ids: list[str]
) -> dict[str, tuple[int, int, float | None]]:
    if not plan_ids:
        return {}
    pc_rows = await db.execute(
        select(PlanCase.plan_id, PlanCase.id).where(PlanCase.plan_id.in_(plan_ids))
    )
    pcs_by_plan: dict[str, list[str]] = defaultdict(list)
    all_pc_ids: list[str] = []
    for plan_id, pc_id in pc_rows.all():
        pcs_by_plan[plan_id].append(pc_id)
        all_pc_ids.append(pc_id)
    result_by_pc: dict[str, ExecuteResult] = {}
    if all_pc_ids:
        res_rows = await db.execute(
            select(PlanCaseResult.plan_case_id, PlanCaseResult.result).where(
                PlanCaseResult.plan_case_id.in_(all_pc_ids)
            )
        )
        result_by_pc = dict(res_rows.all())
    out: dict[str, tuple[int, int, float | None]] = {}
    for plan_id in plan_ids:
        pc_ids = pcs_by_plan.get(plan_id, [])
        total = len(pc_ids)
        not_run = 0
        pass_count = 0
        executed = 0
        for pc_id in pc_ids:
            key = result_by_pc.get(pc_id, ExecuteResult.not_run)
            if key == ExecuteResult.not_run:
                not_run += 1
            else:
                executed += 1
                if key == ExecuteResult.pass_:
                    pass_count += 1
        pass_rate = round(pass_count / executed * 100, 1) if executed else None
        out[plan_id] = (total, not_run, pass_rate)
    return out


def _plan_to_brief(
    plan: TestPlan,
    progress: tuple[int, int, float | None],
    *,
    version: VersionBrief | None = None,
) -> ActivePlanBrief:
    total, not_run, pass_rate = progress
    status = plan.status.value if hasattr(plan.status, "value") else str(plan.status)
    return ActivePlanBrief(
        id=plan.id,
        name=plan.name,
        status=status,
        case_total=total,
        not_run=not_run,
        pass_rate=pass_rate,
        version=version,
    )


async def _unfinished_plans(
    db: AsyncSession, project_id: str
) -> tuple[list[TestPlan], dict[str, VersionBrief]]:
    plans_q = await db.execute(
        select(TestPlan)
        .where(
            TestPlan.project_id == project_id,
            TestPlan.status.in_([PlanStatus.draft, PlanStatus.active]),
        )
        .order_by(TestPlan.updated_at.desc())
        .limit(_PLAN_CHART_LIMIT)
    )
    plans = list(plans_q.scalars().all())
    version_ids = {p.version_id for p in plans if p.version_id}
    ver_map: dict[str, VersionBrief] = {}
    if version_ids:
        ver_rows = await db.execute(
            select(ProjectVersion).where(
                ProjectVersion.id.in_(version_ids),
                ProjectVersion.project_id == project_id,
            )
        )
        ver_map = {v.id: _version_brief(v) for v in ver_rows.scalars().all()}
    return plans, ver_map


async def _plan_focus(db: AsyncSession, project_id: str) -> PlanFocus:
    plans, ver_map = await _unfinished_plans(db, project_id)
    progress_map = await _plan_progress_map(db, [p.id for p in plans])
    results_map = await _plan_case_results_map(db, [p.id for p in plans])
    unfinished_plans = [
        _plan_to_brief(
            p,
            progress_map.get(p.id, (0, 0, None)),
            version=ver_map.get(p.version_id) if p.version_id else None,
        )
        for p in plans
    ]
    points: list[PlanChartPoint] = []
    for plan in plans:
        pc_ids, result_by_pc = results_map.get(plan.id, ([], {}))
        by_result, pass_rate = _execute_result_counts(pc_ids, result_by_pc)
        status = plan.status.value if hasattr(plan.status, "value") else str(plan.status)
        points.append(
            PlanChartPoint(
                plan_id=plan.id,
                plan_name=plan.name,
                status=status,
                by_result=by_result,
                pass_rate=pass_rate,
            )
        )
    return PlanFocus(
        unfinished_plans=unfinished_plans,
        execution_chart=PlanExecutionChart(points=points),
    )


async def _plan_result_counts(db: AsyncSession, plan_id: str) -> tuple[list[StatusCountItem], float | None]:
    plan_map = await _plan_case_results_map(db, [plan_id])
    pc_ids, result_by_pc = plan_map.get(plan_id, ([], {}))
    return _execute_result_counts(pc_ids, result_by_pc)


async def _plan_execution_chart(db: AsyncSession, project_id: str) -> PlanExecutionChart:
    plans_q = await db.execute(
        select(TestPlan)
        .where(
            TestPlan.project_id == project_id,
            TestPlan.status.in_([PlanStatus.draft, PlanStatus.active]),
        )
        .order_by(TestPlan.updated_at.desc())
        .limit(_PLAN_CHART_LIMIT)
    )
    plans = list(plans_q.scalars().all())
    results_map = await _plan_case_results_map(db, [p.id for p in plans])
    points: list[PlanChartPoint] = []
    for plan in plans:
        pc_ids, result_by_pc = results_map.get(plan.id, ([], {}))
        by_result, pass_rate = _execute_result_counts(pc_ids, result_by_pc)
        status = plan.status.value if hasattr(plan.status, "value") else str(plan.status)
        points.append(
            PlanChartPoint(
                plan_id=plan.id,
                plan_name=plan.name,
                status=status,
                by_result=by_result,
                pass_rate=pass_rate,
            )
        )
    return PlanExecutionChart(points=points)


async def _plans_by_status(
    db: AsyncSession, project_id: str, status: PlanStatus, limit: int
) -> list[ActivePlanBrief]:
    result = await db.execute(
        select(TestPlan)
        .where(TestPlan.project_id == project_id, TestPlan.status == status)
        .order_by(TestPlan.updated_at.desc())
        .limit(limit)
    )
    plans = list(result.scalars().all())
    progress_map = await _plan_progress_map(db, [p.id for p in plans])
    return [
        _plan_to_brief(p, progress_map.get(p.id, (0, 0, None))) for p in plans
    ]


async def _requirements_by_status(
    db: AsyncSession,
    project_id: str,
    status: RequirementStatus,
    limit: int,
) -> list[RequirementTodoBrief]:
    result = await db.execute(
        select(Requirement)
        .where(Requirement.project_id == project_id, Requirement.status == status)
        .order_by(Requirement.updated_at.desc())
        .limit(limit)
    )
    rows = list(result.scalars().all())
    version_ids = {r.version_id for r in rows if r.version_id}
    ver_map: dict[str, VersionBrief] = {}
    if version_ids:
        ver_rows = await db.execute(
            select(ProjectVersion).where(ProjectVersion.id.in_(version_ids))
        )
        ver_map = {
            v.id: VersionBrief(id=v.id, num=v.num, name=v.name) for v in ver_rows.scalars().all()
        }
    return [
        RequirementTodoBrief(
            id=row.id,
            num=row.num,
            title=row.title,
            status=row.status,
            version=ver_map.get(row.version_id) if row.version_id else None,
        )
        for row in rows
    ]


async def _bugs_query(
    db: AsyncSession,
    project_id: str,
    *,
    follower_user_id: str | None = None,
    reporter_user_id: str | None = None,
    status_keys: tuple[str, ...] | None = None,
    limit: int = _TODO_LIST_LIMIT,
) -> list[BugOut]:
    stmt = select(Bug).where(Bug.project_id == project_id)
    if status_keys:
        stmt = stmt.where(Bug.status_key.in_(status_keys))
    if follower_user_id:
        stmt = stmt.where(
            Bug.id.in_(
                select(BugFollowerLink.bug_id).where(BugFollowerLink.user_id == follower_user_id)
            )
        )
    if reporter_user_id:
        stmt = stmt.where(Bug.reporter_id == reporter_user_id)
    stmt = stmt.order_by(Bug.updated_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return [bug_out_todo(b) for b in result.scalars().all()]


def _role_key(role: ProjectRole | None, is_system_admin: bool) -> str:
    if is_system_admin:
        return "system_admin"
    if role is None:
        return "member"
    return role.value if hasattr(role, "value") else str(role)


async def _summary_counts_session(project_id: str) -> DashboardSummary:
    """KPI 四条 count 合并为一次查询。"""
    async with async_session_factory() as db:
        row = (
            await db.execute(
                select(
                    select(func.count())
                    .select_from(ProjectVersion)
                    .where(ProjectVersion.project_id == project_id)
                    .scalar_subquery(),
                    select(func.count())
                    .select_from(Requirement)
                    .where(Requirement.project_id == project_id)
                    .scalar_subquery(),
                    select(func.count())
                    .select_from(TestCase)
                    .where(
                        TestCase.project_id == project_id,
                        TestCase.deleted.is_(False),
                    )
                    .scalar_subquery(),
                    select(func.count())
                    .select_from(Bug)
                    .where(Bug.project_id == project_id)
                    .scalar_subquery(),
                )
            )
        ).one()
        return DashboardSummary(
            version_count=int(row[0] or 0),
            requirement_count=int(row[1] or 0),
            case_count=int(row[2] or 0),
            bug_count=int(row[3] or 0),
        )


async def _version_focus_session(project_id: str, version_id: Optional[str]) -> VersionFocus:
    async with async_session_factory() as db:
        return await _version_focus(db, project_id, version_id)


async def _bug_overview_chart_session(project_id: str) -> BugOverviewChart:
    async with async_session_factory() as db:
        return await _bug_overview_chart(db, project_id)


async def _bug_focus_session(project_id: str) -> BugFocus:
    async with async_session_factory() as db:
        return await _bug_focus(db, project_id)


async def _plan_focus_session(project_id: str) -> PlanFocus:
    async with async_session_factory() as db:
        return await _plan_focus(db, project_id)


async def _plan_execution_chart_session(project_id: str) -> PlanExecutionChart:
    async with async_session_factory() as db:
        return await _plan_execution_chart(db, project_id)


async def _plans_by_status_session(
    project_id: str, status: PlanStatus, limit: int
) -> list[ActivePlanBrief]:
    async with async_session_factory() as db:
        return await _plans_by_status(db, project_id, status, limit)


async def _requirements_by_status_session(
    project_id: str, status: RequirementStatus, limit: int
) -> list[RequirementTodoBrief]:
    async with async_session_factory() as db:
        return await _requirements_by_status(db, project_id, status, limit)


async def _bugs_query_session(
    project_id: str,
    *,
    follower_user_id: str | None = None,
    status_keys: tuple[str, ...] | None = None,
    limit: int = _TODO_LIST_LIMIT,
) -> list[BugOut]:
    async with async_session_factory() as db:
        return await _bugs_query(
            db,
            project_id,
            follower_user_id=follower_user_id,
            status_keys=status_keys,
            limit=limit,
        )


async def _build_todo_tester(project_id: str) -> DashboardTodo:
    (
        draft_plans,
        active_plans,
        fixed_bugs,
        not_tested_requirements,
        testing_requirements,
    ) = await asyncio.gather(
        _plans_by_status_session(project_id, PlanStatus.draft, _TODO_LIST_LIMIT),
        _plans_by_status_session(project_id, PlanStatus.active, _TODO_LIST_LIMIT),
        _bugs_query_session(project_id, status_keys=(TESTER_FIXED_BUG_STATUS_KEY,)),
        _requirements_by_status_session(project_id, RequirementStatus.not_tested, _TODO_LIST_LIMIT),
        _requirements_by_status_session(project_id, RequirementStatus.testing, _TODO_LIST_LIMIT),
    )
    return DashboardTodo(
        draft_plans=draft_plans,
        active_plans_todo=active_plans,
        fixed_bugs=fixed_bugs,
        not_tested_requirements=not_tested_requirements,
        testing_requirements=testing_requirements,
    )


async def _build_todo_member(project_id: str, user_id: str) -> DashboardTodo:
    follower_todo_bugs = await _bugs_query_session(
        project_id,
        follower_user_id=user_id,
        status_keys=MEMBER_FOLLOWER_TODO_STATUS_KEYS,
    )
    return DashboardTodo(follower_todo_bugs=follower_todo_bugs)


@router.get("", response_model=DashboardWorkbench)
async def workbench(
    version_id: Optional[str] = Query(default=None),
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    role = await get_project_role(ctx.user, ctx.project_id, db)
    role_key = _role_key(role, ctx.user.is_system_admin)
    project_id = ctx.project_id
    is_tester_side = role in (ProjectRole.tester, ProjectRole.project_admin) or ctx.user.is_system_admin

    summary_task = _summary_counts_session(project_id)
    overview_task = asyncio.gather(
        _version_focus_session(project_id, version_id),
        _bug_focus_session(project_id),
        _plan_focus_session(project_id),
    )
    todo_task = (
        _build_todo_tester(project_id)
        if is_tester_side
        else _build_todo_member(project_id, ctx.user.id)
    )

    summary, overview_parts, todo = await asyncio.gather(summary_task, overview_task, todo_task)
    version_focus, bug_focus, plan_focus = overview_parts

    overview = DashboardOverview(
        version_focus=version_focus,
        bug_focus=bug_focus,
        plan_focus=plan_focus,
    )
    return DashboardWorkbench(
        summary=summary,
        overview=overview,
        todo=todo,
        project_role=role_key,
    )
