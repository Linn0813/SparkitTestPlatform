from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text, case as sql_case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import ProjectContext, require_project_context
from app.models.bug import Bug, BugStatusHistory
from app.models.project_version import ProjectVersion
from app.models.requirement import (
    BugRequirementLink,
    Requirement,
    RequirementNodeTask,
)
from app.models.template import BugStatus
from app.models.user import User
from app.schemas.quality import (
    BugResponseTimeItem,
    BugResponseTimeOut,
    BugReflowRateOut,
    BugSourceTrendItem,
    DeveloperBugRateItem,
    LeakageRateOut,
    QualityDashboardOut,
    RequirementBugDensityItem,
    StaleRequirementItem,
    VersionBriefOut,
    VersionDeliveryHealth,
)

router = APIRouter(prefix="/quality", tags=["quality"])

_COMPLETED_STATUSES = {"released", "completed"}
_INCOMPLETE_STATUSES = {"draft", "pending_review", "designing", "developing", "testing", "pending_release"}

_STALE_THRESHOLDS = {
    "designing":        {"warning": 5,  "danger": 10},
    "developing":       {"warning": 7,  "danger": 14},
    "testing":          {"warning": 3,  "danger": 7},
    "pending_release":  {"warning": 2,  "danger": 5},
}

# Bug 自定义字段 key（根据项目实际配置）
_SEVERITY_KEY = "severity"          # 严重程度字段 key
_SOURCE_KEY = "source"              # 发现来源字段 key
_SOURCE_ONLINE = "线上反馈"
_SOURCE_INTERNAL = "内部体验"
_SOURCE_TESTING = "需求测试"
_SEVERITY_CRITICAL = "严重"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# 获取项目可用版本列表
# ---------------------------------------------------------------------------

async def _get_versions(db: AsyncSession, project_id: str) -> list[ProjectVersion]:
    result = await db.execute(
        select(ProjectVersion)
        .where(ProjectVersion.project_id == project_id)
        .order_by(ProjectVersion.num.desc())
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# 获取终态 status_key 集合
# ---------------------------------------------------------------------------

async def _get_terminal_keys(db: AsyncSession, project_id: str) -> set[str]:
    result = await db.execute(
        select(BugStatus.key).where(
            BugStatus.project_id == project_id,
            BugStatus.is_terminal.is_(True),
        )
    )
    return {r for r in result.scalars().all()}


# ---------------------------------------------------------------------------
# 构建 bugs 基础查询条件
# ---------------------------------------------------------------------------

def _bug_version_filter(version_ids: list[str]):
    if not version_ids:
        return None
    return Bug.plan_version_id.in_(version_ids)


# ---------------------------------------------------------------------------
# 1. 需求 Bug 密度
# ---------------------------------------------------------------------------

async def _requirement_bug_density(
    db: AsyncSession, project_id: str, version_ids: list[str]
) -> list[RequirementBugDensityItem]:
    # 需求列表（版本筛选）
    req_stmt = select(Requirement).where(Requirement.project_id == project_id)
    if version_ids:
        req_stmt = req_stmt.where(Requirement.version_id.in_(version_ids))
    reqs = (await db.execute(req_stmt)).scalars().all()
    if not reqs:
        return []

    req_ids = [r.id for r in reqs]

    # 每个需求的关联 bug 数
    bug_counts_result = await db.execute(
        select(BugRequirementLink.requirement_id, func.count(BugRequirementLink.bug_id))
        .where(BugRequirementLink.requirement_id.in_(req_ids))
        .group_by(BugRequirementLink.requirement_id)
    )
    bug_counts = {row[0]: row[1] for row in bug_counts_result.all()}

    # 每个需求的 estimate_points 总和
    ep_result = await db.execute(
        select(RequirementNodeTask.requirement_id, func.sum(RequirementNodeTask.estimate_points))
        .where(RequirementNodeTask.requirement_id.in_(req_ids))
        .group_by(RequirementNodeTask.requirement_id)
    )
    ep_map = {row[0]: float(row[1]) if row[1] else 0.0 for row in ep_result.all()}

    items = []
    for req in reqs:
        bc = bug_counts.get(req.id, 0)
        ep = ep_map.get(req.id, 0.0)
        density = round(bc / ep, 2) if ep > 0 else None
        items.append(RequirementBugDensityItem(
            requirement_id=req.id,
            requirement_num=req.num,
            title=req.title,
            priority=req.priority,
            bug_count=bc,
            estimate_points=ep,
            density=density,
        ))

    return sorted(items, key=lambda x: (x.density or -1), reverse=True)


# ---------------------------------------------------------------------------
# 2. 高优需求停滞预警
# ---------------------------------------------------------------------------

async def _stale_requirements(
    db: AsyncSession, project_id: str
) -> list[StaleRequirementItem]:
    stmt = select(Requirement).where(
        Requirement.project_id == project_id,
        Requirement.priority.in_(["p00", "p0"]),
        Requirement.status.in_(list(_STALE_THRESHOLDS.keys())),
    )
    reqs = (await db.execute(stmt)).scalars().all()
    if not reqs:
        return []

    user_ids = set()
    for r in reqs:
        for uid in [r.frontend_rd_id, r.backend_rd_id, r.qa_id]:
            if uid:
                user_ids.add(uid)

    user_map: dict[str, str] = {}
    if user_ids:
        users = (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
        user_map = {u.id: u.name for u in users}

    now = _now()
    items = []
    for req in reqs:
        stale_days = (now - req.updated_at).days
        thresholds = _STALE_THRESHOLDS.get(req.status, {"warning": 7, "danger": 14})
        if stale_days >= thresholds["danger"]:
            level = "danger"
        elif stale_days >= thresholds["warning"]:
            level = "warning"
        else:
            continue  # 未达到阈值不展示

        items.append(StaleRequirementItem(
            requirement_id=req.id,
            requirement_num=req.num,
            title=req.title,
            priority=req.priority,
            status=req.status,
            stale_days=stale_days,
            warning_level=level,
            frontend_rd_name=user_map.get(req.frontend_rd_id) if req.frontend_rd_id else None,
            backend_rd_name=user_map.get(req.backend_rd_id) if req.backend_rd_id else None,
            qa_name=user_map.get(req.qa_id) if req.qa_id else None,
        ))

    return sorted(items, key=lambda x: x.stale_days, reverse=True)


# ---------------------------------------------------------------------------
# 3. 需求交付健康度（按版本）
# ---------------------------------------------------------------------------

async def _version_delivery_health(
    db: AsyncSession, project_id: str, version_ids: list[str]
) -> list[VersionDeliveryHealth]:
    # 获取版本信息
    v_stmt = select(ProjectVersion).where(ProjectVersion.project_id == project_id)
    if version_ids:
        v_stmt = v_stmt.where(ProjectVersion.id.in_(version_ids))
    versions = (await db.execute(v_stmt)).scalars().all()
    if not versions:
        return []

    vid_list = [v.id for v in versions]
    version_map = {v.id: v for v in versions}

    # 各版本需求状态分布
    req_result = await db.execute(
        select(Requirement.version_id, Requirement.status, func.count(Requirement.id))
        .where(Requirement.project_id == project_id, Requirement.version_id.in_(vid_list))
        .group_by(Requirement.version_id, Requirement.status)
    )
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for vid, status, cnt in req_result.all():
        counts[vid][status] = cnt

    items = []
    for v in versions:
        status_counts = counts[v.id]
        total = sum(status_counts.values())
        completed = sum(status_counts.get(s, 0) for s in _COMPLETED_STATUSES)
        incomplete = total - completed
        rate = round(completed / total * 100, 1) if total > 0 else 0.0
        at_risk = v.status in ("releasing", "reviewing", "ended") and incomplete > 0

        items.append(VersionDeliveryHealth(
            version_id=v.id,
            version_name=v.name,
            version_status=v.status,
            total_requirements=total,
            completed_requirements=completed,
            incomplete_requirements=incomplete,
            completion_rate=rate,
            at_risk=at_risk,
        ))

    return items


# ---------------------------------------------------------------------------
# 4. 漏测率
# ---------------------------------------------------------------------------

async def _leakage_rate(
    db: AsyncSession, project_id: str, version_ids: list[str]
) -> LeakageRateOut:
    # 用 SQL 聚合，避免把所有 bug 加载到 Python
    base = select(
        func.count(Bug.id).label("total"),
        func.sum(
            sql_case(
                (func.json_unquote(func.json_extract(Bug.custom_fields, f'$."{_SOURCE_KEY}"')) == _SOURCE_ONLINE, 1),
                else_=0,
            )
        ).label("online"),
    ).where(Bug.project_id == project_id)
    if version_ids:
        base = base.where(Bug.plan_version_id.in_(version_ids))

    row = (await db.execute(base)).one()
    total = int(row.total or 0)
    online = int(row.online or 0)
    rate = round(online / total * 100, 1) if total > 0 else 0.0

    # 按版本趋势（SQL 聚合）
    trend_stmt = select(
        Bug.plan_version_id,
        func.count(Bug.id).label("total"),
        func.sum(
            sql_case(
                (func.json_unquote(func.json_extract(Bug.custom_fields, f'$."{_SOURCE_KEY}"')) == _SOURCE_ONLINE, 1),
                else_=0,
            )
        ).label("online"),
    ).where(
        Bug.project_id == project_id,
        Bug.plan_version_id.isnot(None),
    )
    if version_ids:
        trend_stmt = trend_stmt.where(Bug.plan_version_id.in_(version_ids))
    trend_stmt = trend_stmt.group_by(Bug.plan_version_id)

    trend_rows = (await db.execute(trend_stmt)).all()

    version_ids_found = [r.plan_version_id for r in trend_rows if r.plan_version_id]
    version_names: dict[str, str] = {}
    if version_ids_found:
        vr = await db.execute(select(ProjectVersion).where(ProjectVersion.id.in_(version_ids_found)))
        version_names = {v.id: v.name for v in vr.scalars().all()}

    trend = [
        {
            "version_name": version_names.get(r.plan_version_id, r.plan_version_id),
            "total": int(r.total or 0),
            "online": int(r.online or 0),
            "rate": round(int(r.online or 0) / int(r.total) * 100, 1) if r.total else 0.0,
        }
        for r in trend_rows
    ]

    return LeakageRateOut(total_bugs=total, online_bugs=online, leakage_rate=rate, by_version=trend)


# ---------------------------------------------------------------------------
# 5. Bug 修复反弹率
# ---------------------------------------------------------------------------

async def _reflow_rate(
    db: AsyncSession, project_id: str, version_ids: list[str], terminal_keys: set[str]
) -> BugReflowRateOut:
    if not terminal_keys:
        return BugReflowRateOut(resolved_bugs=0, reflowed_bugs=0, reflow_rate=0.0, reflow_bug_list=[])

    # 先用 SQL 找出该项目范围内的 bug_id
    bug_id_stmt = select(Bug.id).where(Bug.project_id == project_id)
    if version_ids:
        bug_id_stmt = bug_id_stmt.where(Bug.plan_version_id.in_(version_ids))
    bug_id_rows = (await db.execute(bug_id_stmt)).all()
    bug_ids = [r[0] for r in bug_id_rows]
    if not bug_ids:
        return BugReflowRateOut(resolved_bugs=0, reflowed_bugs=0, reflow_rate=0.0, reflow_bug_list=[])

    # 只拉 to_status 字段（不拉全部列），按时间排序
    history_result = await db.execute(
        select(BugStatusHistory.bug_id, BugStatusHistory.to_status)
        .where(BugStatusHistory.bug_id.in_(bug_ids))
        .order_by(BugStatusHistory.bug_id, BugStatusHistory.created_at)
    )
    histories: dict[str, list[str]] = defaultdict(list)
    for bug_id, to_status in history_result.all():
        histories[bug_id].append(to_status)

    resolved_bugs: set[str] = set()
    reflowed: dict[str, int] = defaultdict(int)

    for bug_id, statuses in histories.items():
        was_terminal = False
        for to_status in statuses:
            if to_status in terminal_keys:
                was_terminal = True
                resolved_bugs.add(bug_id)
            elif was_terminal and to_status not in terminal_keys:
                reflowed[bug_id] += 1
                was_terminal = False

    reflow_count = len(reflowed)
    resolved_count = len(resolved_bugs)
    rate = round(reflow_count / resolved_count * 100, 1) if resolved_count > 0 else 0.0

    if not reflowed:
        return BugReflowRateOut(
            resolved_bugs=resolved_count,
            reflowed_bugs=0,
            reflow_rate=0.0,
            reflow_bug_list=[],
        )

    # 只查反弹的 bug 详情
    reflow_bug_rows = (await db.execute(
        select(Bug.id, Bug.num, Bug.title, Bug.assignee_id)
        .where(Bug.id.in_(list(reflowed.keys())))
    )).all()

    assignee_ids = {r.assignee_id for r in reflow_bug_rows if r.assignee_id}
    user_map: dict[str, str] = {}
    if assignee_ids:
        users = (await db.execute(select(User).where(User.id.in_(assignee_ids)))).scalars().all()
        user_map = {u.id: u.name for u in users}

    bug_info = {r.id: r for r in reflow_bug_rows}
    reflow_list = [
        {
            "bug_num": bug_info[bid].num,
            "title": bug_info[bid].title,
            "reflow_count": cnt,
            "assignee_name": user_map.get(bug_info[bid].assignee_id) if bug_info[bid].assignee_id else None,
        }
        for bid, cnt in sorted(reflowed.items(), key=lambda x: x[1], reverse=True)
        if bid in bug_info
    ]

    return BugReflowRateOut(
        resolved_bugs=resolved_count,
        reflowed_bugs=reflow_count,
        reflow_rate=rate,
        reflow_bug_list=reflow_list,
    )


# ---------------------------------------------------------------------------
# 6. 研发人员 Bug 引入率
# ---------------------------------------------------------------------------

async def _developer_bug_rate(
    db: AsyncSession, project_id: str, version_ids: list[str]
) -> list[DeveloperBugRateItem]:
    req_stmt = select(Requirement).where(Requirement.project_id == project_id)
    if version_ids:
        req_stmt = req_stmt.where(Requirement.version_id.in_(version_ids))
    reqs = (await db.execute(req_stmt)).scalars().all()
    if not reqs:
        return []

    req_ids = [r.id for r in reqs]

    # 关联 bug 数
    bug_result = await db.execute(
        select(BugRequirementLink.requirement_id, func.count(BugRequirementLink.bug_id))
        .where(BugRequirementLink.requirement_id.in_(req_ids))
        .group_by(BugRequirementLink.requirement_id)
    )
    bug_counts = {row[0]: row[1] for row in bug_result.all()}

    # estimate_points
    ep_result = await db.execute(
        select(RequirementNodeTask.requirement_id, func.sum(RequirementNodeTask.estimate_points))
        .where(RequirementNodeTask.requirement_id.in_(req_ids))
        .group_by(RequirementNodeTask.requirement_id)
    )
    ep_map = {row[0]: float(row[1]) if row[1] else 0.0 for row in ep_result.all()}

    # 按研发负责人聚合
    dev_data: dict[str, dict] = defaultdict(lambda: {"req_count": 0, "bug_count": 0, "ep": 0.0})
    dev_ids: set[str] = set()

    for req in reqs:
        rd_ids = [req.frontend_rd_id, req.backend_rd_id]
        for rd_id in rd_ids:
            if not rd_id:
                continue
            dev_ids.add(rd_id)
            dev_data[rd_id]["req_count"] += 1
            dev_data[rd_id]["bug_count"] += bug_counts.get(req.id, 0)
            dev_data[rd_id]["ep"] += ep_map.get(req.id, 0.0)

    if not dev_ids:
        return []

    users = (await db.execute(select(User).where(User.id.in_(dev_ids)))).scalars().all()
    user_map = {u.id: u.name for u in users}

    items = []
    for uid, d in dev_data.items():
        ep = d["ep"]
        bc = d["bug_count"]
        rate = round(bc / ep, 2) if ep > 0 else None
        items.append(DeveloperBugRateItem(
            user_id=uid,
            user_name=user_map.get(uid, uid),
            requirement_count=d["req_count"],
            bug_count=bc,
            estimate_points=ep,
            bug_rate=rate,
        ))

    return sorted(items, key=lambda x: (x.bug_rate or -1), reverse=True)


# ---------------------------------------------------------------------------
# 7. P0/P1 Bug 响应时效
# ---------------------------------------------------------------------------

async def _bug_response_time(
    db: AsyncSession, project_id: str, version_ids: list[str]
) -> BugResponseTimeOut:
    # 在 SQL 里直接过滤严重 bug，不加载全表
    stmt = select(Bug).where(
        Bug.project_id == project_id,
        func.json_unquote(func.json_extract(Bug.custom_fields, f'$."{_SEVERITY_KEY}"')) == _SEVERITY_CRITICAL,
    )
    if version_ids:
        stmt = stmt.where(Bug.plan_version_id.in_(version_ids))
    bugs = (await db.execute(stmt)).scalars().all()

    if not bugs:
        return BugResponseTimeOut(avg_response_hours=None, items=[])

    bug_ids = [b.id for b in bugs]
    bug_map = {b.id: b for b in bugs}

    # 每个 bug 的第一次状态变更时间
    first_history_result = await db.execute(
        select(BugStatusHistory.bug_id, func.min(BugStatusHistory.created_at))
        .where(BugStatusHistory.bug_id.in_(bug_ids))
        .group_by(BugStatusHistory.bug_id)
    )
    first_response: dict[str, datetime] = {row[0]: row[1] for row in first_history_result.all()}

    assignee_ids = {b.assignee_id for b in bugs if b.assignee_id}
    user_map: dict[str, str] = {}
    if assignee_ids:
        users = (await db.execute(select(User).where(User.id.in_(assignee_ids)))).scalars().all()
        user_map = {u.id: u.name for u in users}

    now = _now()
    total_hours = 0.0
    responded_count = 0
    items = []

    for b in bugs:
        resp_time = first_response.get(b.id)
        if resp_time:
            hours = round((resp_time - b.created_at).total_seconds() / 3600, 1)
            total_hours += hours
            responded_count += 1
            level = "ok" if hours <= 4 else "warning" if hours <= 24 else "danger"
        else:
            hours = None
            level = "unhandled"

        items.append(BugResponseTimeItem(
            bug_id=b.id,
            bug_num=b.num,
            title=b.title,
            severity=b.custom_fields.get(_SEVERITY_KEY, ""),
            created_at=b.created_at.isoformat(),
            first_response_hours=hours,
            warning_level=level,
            assignee_name=user_map.get(b.assignee_id) if b.assignee_id else None,
        ))

    avg = round(total_hours / responded_count, 1) if responded_count > 0 else None
    items.sort(key=lambda x: (x.warning_level != "unhandled", x.first_response_hours or 9999), reverse=True)
    return BugResponseTimeOut(avg_response_hours=avg, items=items)


# ---------------------------------------------------------------------------
# 8. Bug 来源分布趋势
# ---------------------------------------------------------------------------

async def _bug_source_trend(
    db: AsyncSession, project_id: str, version_ids: list[str]
) -> list[BugSourceTrendItem]:
    stmt = select(
        Bug.plan_version_id,
        func.json_unquote(func.json_extract(Bug.custom_fields, f'$."{_SOURCE_KEY}"')).label("source"),
        func.count(Bug.id).label("cnt"),
    ).where(Bug.project_id == project_id)
    if version_ids:
        stmt = stmt.where(Bug.plan_version_id.in_(version_ids))
    stmt = stmt.group_by(Bug.plan_version_id, text(f'JSON_UNQUOTE(JSON_EXTRACT(custom_fields, \'$."{_SOURCE_KEY}"\'))'))

    rows = (await db.execute(stmt)).all()
    if not rows:
        return []

    # 聚合
    by_version: dict[str, dict] = defaultdict(lambda: {"online": 0, "internal": 0, "testing": 0, "other": 0})
    version_ids_found: set[str] = set()

    for r in rows:
        vid = r.plan_version_id or "__no_version__"
        if r.plan_version_id:
            version_ids_found.add(r.plan_version_id)
        cnt = int(r.cnt or 0)
        source = r.source or ""
        if source == _SOURCE_ONLINE:
            by_version[vid]["online"] += cnt
        elif source == _SOURCE_INTERNAL:
            by_version[vid]["internal"] += cnt
        elif source == _SOURCE_TESTING:
            by_version[vid]["testing"] += cnt
        else:
            by_version[vid]["other"] += cnt

    version_names: dict[str, str] = {}
    if version_ids_found:
        vr = await db.execute(select(ProjectVersion).where(ProjectVersion.id.in_(version_ids_found)))
        version_names = {v.id: v.name for v in vr.scalars().all()}

    return [
        BugSourceTrendItem(
            label=version_names.get(vid, "未关联版本") if vid != "__no_version__" else "未关联版本",
            online=d["online"],
            internal=d["internal"],
            testing=d["testing"],
            other=d["other"],
        )
        for vid, d in by_version.items()
    ]


# ---------------------------------------------------------------------------
# 子接口（各自独立，前端并发请求）
# ---------------------------------------------------------------------------

@router.get("/versions", response_model=list[VersionBriefOut])
async def get_quality_versions(
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    versions = await _get_versions(db, ctx.project_id)
    return [VersionBriefOut(id=v.id, num=v.num, name=v.name) for v in versions]


@router.get("/requirement-bug-density", response_model=list[RequirementBugDensityItem])
async def get_requirement_bug_density(
    version_ids: Optional[list[str]] = Query(default=None),
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    return await _requirement_bug_density(db, ctx.project_id, version_ids or [])


@router.get("/stale-requirements", response_model=list[StaleRequirementItem])
async def get_stale_requirements(
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    return await _stale_requirements(db, ctx.project_id)


@router.get("/version-delivery-health", response_model=list[VersionDeliveryHealth])
async def get_version_delivery_health(
    version_ids: Optional[list[str]] = Query(default=None),
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    return await _version_delivery_health(db, ctx.project_id, version_ids or [])


@router.get("/leakage-rate", response_model=LeakageRateOut)
async def get_leakage_rate(
    version_ids: Optional[list[str]] = Query(default=None),
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    return await _leakage_rate(db, ctx.project_id, version_ids or [])


@router.get("/reflow-rate", response_model=BugReflowRateOut)
async def get_reflow_rate(
    version_ids: Optional[list[str]] = Query(default=None),
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    terminal_keys = await _get_terminal_keys(db, ctx.project_id)
    return await _reflow_rate(db, ctx.project_id, version_ids or [], terminal_keys)


@router.get("/developer-bug-rate", response_model=list[DeveloperBugRateItem])
async def get_developer_bug_rate(
    version_ids: Optional[list[str]] = Query(default=None),
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    return await _developer_bug_rate(db, ctx.project_id, version_ids or [])


@router.get("/bug-response-time", response_model=BugResponseTimeOut)
async def get_bug_response_time(
    version_ids: Optional[list[str]] = Query(default=None),
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    return await _bug_response_time(db, ctx.project_id, version_ids or [])


@router.get("/bug-source-trend", response_model=list[BugSourceTrendItem])
async def get_bug_source_trend(
    version_ids: Optional[list[str]] = Query(default=None),
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    return await _bug_source_trend(db, ctx.project_id, version_ids or [])
