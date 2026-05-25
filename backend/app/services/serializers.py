from __future__ import annotations

from collections import defaultdict
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bug import Bug, BugFollowerLink
from app.models.case import TestCase
from app.models.project_version import ProjectVersion
from app.models.requirement import BugPlanLink, BugRequirementLink
from app.models.user import User
from app.schemas.bug import BugFollowerScheduleOut, BugOut
from app.schemas.case import TestCaseOut
from app.schemas.user import UserOut
from app.schemas.version import VersionBrief
from app.services.links import get_case_requirement_ids


def _version_brief_from_row(row: ProjectVersion) -> VersionBrief:
    return VersionBrief(id=row.id, num=row.num, name=row.name, released_at=row.released_at)


async def _version_brief(db: AsyncSession, version_id: str | None) -> VersionBrief | None:
    if not version_id:
        return None
    row = await db.get(ProjectVersion, version_id)
    if not row:
        return None
    return _version_brief_from_row(row)


def bug_out_todo(bug: Bug, *, plan_version: VersionBrief | None = None) -> BugOut:
    """工作台待办列表：仅用 Bug 行字段，避免关联查询。"""
    return BugOut(
        id=bug.id,
        project_id=bug.project_id,
        num=bug.num,
        title=bug.title,
        status_key=bug.status_key,
        assignee_id=bug.assignee_id,
        reporter_id=bug.reporter_id,
        description=bug.description,
        custom_fields=bug.custom_fields or {},
        requirement_ids=[],
        plan_ids=[],
        plan_version_id=bug.plan_version_id,
        found_version_id=bug.found_version_id,
        plan_version=plan_version,
        found_version=None,
        follower_ids=[],
        created_at=bug.created_at,
        updated_at=bug.updated_at,
        assignee=None,
        reporter=None,
        followers=[],
    )


async def bug_out_list_batch(bugs: list[Bug], db: AsyncSession) -> list[BugOut]:
    """缺陷列表：批量加载关联，避免逐条 N+1。"""
    if not bugs:
        return []

    bug_ids = [b.id for b in bugs]
    user_ids: set[str] = set()
    version_ids: set[str] = set()
    for b in bugs:
        if b.assignee_id:
            user_ids.add(b.assignee_id)
        user_ids.add(b.reporter_id)
        if b.plan_version_id:
            version_ids.add(b.plan_version_id)
        if b.found_version_id:
            version_ids.add(b.found_version_id)

    req_by_bug: dict[str, list[str]] = defaultdict(list)
    req_rows = await db.execute(
        select(BugRequirementLink.bug_id, BugRequirementLink.requirement_id).where(
            BugRequirementLink.bug_id.in_(bug_ids)
        )
    )
    for bug_id, req_id in req_rows.all():
        req_by_bug[bug_id].append(req_id)

    plan_by_bug: dict[str, list[str]] = defaultdict(list)
    plan_rows = await db.execute(
        select(BugPlanLink.bug_id, BugPlanLink.plan_id).where(BugPlanLink.bug_id.in_(bug_ids))
    )
    for bug_id, plan_id in plan_rows.all():
        plan_by_bug[bug_id].append(plan_id)

    follower_by_bug: dict[str, list[str]] = defaultdict(list)
    follower_schedules_by_bug: dict[str, list[BugFollowerScheduleOut]] = defaultdict(list)
    follower_rows = await db.execute(
        select(BugFollowerLink).where(BugFollowerLink.bug_id.in_(bug_ids))
    )
    for link in follower_rows.scalars().all():
        follower_by_bug[link.bug_id].append(link.user_id)
        user_ids.add(link.user_id)
        follower_schedules_by_bug[link.bug_id].append(
            BugFollowerScheduleOut(
                link_id=link.id,
                user_id=link.user_id,
                fix_estimate_points=link.fix_estimate_points,
                scheduled_start=link.scheduled_start,
                scheduled_end=link.scheduled_end,
            )
        )

    users_map: dict[str, User] = {}
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users_map = {u.id: u for u in users_result.scalars().all()}

    versions_map: dict[str, VersionBrief] = {}
    if version_ids:
        ver_rows = await db.execute(
            select(ProjectVersion).where(ProjectVersion.id.in_(version_ids))
        )
        versions_map = {v.id: _version_brief_from_row(v) for v in ver_rows.scalars().all()}

    out: list[BugOut] = []
    for b in bugs:
        follower_ids = follower_by_bug.get(b.id, [])
        assignee = users_map.get(b.assignee_id) if b.assignee_id else None
        reporter = users_map.get(b.reporter_id)
        followers = [
            UserOut.model_validate(users_map[fid])
            for fid in follower_ids
            if fid in users_map
        ]
        out.append(
            BugOut(
                id=b.id,
                project_id=b.project_id,
                num=b.num,
                title=b.title,
                status_key=b.status_key,
                assignee_id=b.assignee_id,
                reporter_id=b.reporter_id,
                description=b.description,
                custom_fields=b.custom_fields or {},
                requirement_ids=req_by_bug.get(b.id, []),
                plan_ids=plan_by_bug.get(b.id, []),
                plan_version_id=b.plan_version_id,
                found_version_id=b.found_version_id,
                plan_version=versions_map.get(b.plan_version_id) if b.plan_version_id else None,
                found_version=versions_map.get(b.found_version_id) if b.found_version_id else None,
                follower_ids=follower_ids,
                follower_schedules=follower_schedules_by_bug.get(b.id, []),
                created_at=b.created_at,
                updated_at=b.updated_at,
                assignee=UserOut.model_validate(assignee) if assignee else None,
                reporter=UserOut.model_validate(reporter) if reporter else None,
                followers=followers,
            )
        )
    return out


async def bug_out(bug: Bug, db: AsyncSession) -> BugOut:
    items = await bug_out_list_batch([bug], db)
    return items[0]


async def case_out(
    case: TestCase,
    db: AsyncSession,
    *,
    module_path: Optional[str] = None,
) -> TestCaseOut:
    req_ids = await get_case_requirement_ids(db, case.id)
    return TestCaseOut(
        id=case.id,
        project_id=case.project_id,
        module_id=case.module_id,
        module_path=module_path,
        title=case.title,
        priority=case.priority,
        precondition=case.precondition,
        step_text=case.step_text,
        expected_result=case.expected_result,
        steps=case.steps or [],
        tags=case.tags or [],
        custom_fields=case.custom_fields or {},
        requirement_ids=req_ids,
        created_by=case.created_by,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )
