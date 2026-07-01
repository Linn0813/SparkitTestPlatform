from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Protocol

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bug import Bug, BugFollowerLink
from app.models.project import ProjectMember
from app.models.requirement import (
    Requirement,
    RequirementNodeProgress,
    RequirementNodeState,
    RequirementNodeTask,
)
from app.models.user import User
from app.schemas.member_schedule import (
    MemberScheduleItemOut,
    MemberScheduleOut,
    MemberScheduleRowOut,
)
from app.services.bug_follower_schedule import _is_schedule_participating
from app.services.requirement_config import load_project_workflow_defs_for_project


def _estimate_value(points: Optional[float]) -> float:
    return float(points) if points is not None else 0.0


class _HasScheduleDates(Protocol):
    scheduled_start: Optional[date]
    scheduled_end: Optional[date]


def _is_fully_scheduled(entity: _HasScheduleDates) -> bool:
    return entity.scheduled_start is not None and entity.scheduled_end is not None


def _overlaps_range(entity: _HasScheduleDates, range_start: date, range_end: date) -> bool:
    assert entity.scheduled_start is not None and entity.scheduled_end is not None
    return entity.scheduled_start <= range_end and entity.scheduled_end >= range_start


def _skip_unscheduled_for_node_state(progress: RequirementNodeProgress | None) -> bool:
    """已完成/已跳过的节点仅作状态，无日历排期时不进「未排期」。"""
    if progress is None:
        return False
    return progress.state in (RequirementNodeState.completed, RequirementNodeState.skipped)


@dataclass
class _MemberBucket:
    scheduled: list[MemberScheduleItemOut] = field(default_factory=list)
    unscheduled: list[MemberScheduleItemOut] = field(default_factory=list)


def _build_task_item(
    task: RequirementNodeTask,
    req: Requirement,
    node_labels: dict[str, str],
    req_task_counts: dict[str, int],
) -> MemberScheduleItemOut:
    return MemberScheduleItemOut(
        item_type="requirement_node_task",
        id=task.id,
        title=task.title,
        assignee_id=task.assignee_id or "",
        estimate_points=task.estimate_points,
        scheduled_start=task.scheduled_start,
        scheduled_end=task.scheduled_end,
        requirement_id=req.id,
        requirement_num=req.num,
        requirement_title=req.title,
        requirement_task_count=req_task_counts.get(req.id, 1),
        node_key=task.node_key,
        node_label=node_labels.get(task.node_key, task.node_key),
        role_key=task.role_key,
    )


def _build_bug_item(link: BugFollowerLink, bug: Bug) -> MemberScheduleItemOut:
    return MemberScheduleItemOut(
        item_type="bug",
        id=link.id,
        title=bug.title,
        assignee_id=link.user_id,
        estimate_points=link.fix_estimate_points,
        scheduled_start=link.scheduled_start,
        scheduled_end=link.scheduled_end,
        bug_id=bug.id,
        bug_num=bug.num,
        bug_title=bug.title,
        node_label="缺陷修复",
    )


def _append_item_to_bucket(
    buckets: dict[str, _MemberBucket],
    assignee_id: str,
    item: MemberScheduleItemOut,
    entity: _HasScheduleDates,
    range_start: date,
    range_end: date,
) -> None:
    if assignee_id not in buckets:
        buckets[assignee_id] = _MemberBucket()
    bucket = buckets[assignee_id]
    if not _is_fully_scheduled(entity):
        bucket.unscheduled.append(item)
    elif _overlaps_range(entity, range_start, range_end):
        bucket.scheduled.append(item)


async def build_member_schedule(
    db: AsyncSession,
    project_id: str,
    range_start: date,
    range_end: date,
) -> MemberScheduleOut:
    if range_start > range_end:
        range_start, range_end = range_end, range_start

    members_result = await db.execute(
        select(ProjectMember, User)
        .join(User, User.id == ProjectMember.user_id)
        .where(ProjectMember.project_id == project_id)
        .order_by(User.name, User.id)
    )
    member_rows = members_result.all()

    tasks_result = await db.execute(
        select(RequirementNodeTask, Requirement, RequirementNodeProgress)
        .join(Requirement, Requirement.id == RequirementNodeTask.requirement_id)
        .outerjoin(
            RequirementNodeProgress,
            (RequirementNodeProgress.requirement_id == RequirementNodeTask.requirement_id)
            & (RequirementNodeProgress.node_key == RequirementNodeTask.node_key),
        )
        .where(Requirement.project_id == project_id)
        .where(RequirementNodeTask.assignee_id.isnot(None))
        .where(
            or_(
                RequirementNodeTask.scheduled_start.is_(None),
                (RequirementNodeTask.scheduled_start <= range_end)
                & (RequirementNodeTask.scheduled_end >= range_start),
            )
        )
        .order_by(
            RequirementNodeTask.assignee_id,
            RequirementNodeTask.scheduled_start,
            RequirementNodeTask.sort,
            RequirementNodeTask.created_at,
        )
    )
    task_rows = tasks_result.all()

    # 获取视窗内涉及的需求的总节点任务数（用于前端判断是否显示为 group）
    req_ids = {task.requirement_id for task, _, _ in task_rows if task.requirement_id}
    req_task_counts: dict[str, int] = {}
    if req_ids:
        count_result = await db.execute(
            select(RequirementNodeTask.requirement_id, func.count())
            .where(RequirementNodeTask.requirement_id.in_(req_ids))
            .group_by(RequirementNodeTask.requirement_id)
        )
        req_task_counts = {req_id: count for req_id, count in count_result.all()}

    bug_links_result = await db.execute(
        select(BugFollowerLink, Bug)
        .join(Bug, Bug.id == BugFollowerLink.bug_id)
        .where(Bug.project_id == project_id)
        .where(
            or_(
                BugFollowerLink.scheduled_start.is_(None),
                (BugFollowerLink.scheduled_start <= range_end)
                & (BugFollowerLink.scheduled_end >= range_start),
            )
        )
        .order_by(BugFollowerLink.user_id, Bug.num, BugFollowerLink.id)
    )
    bug_link_rows = bug_links_result.all()

    node_defs = await load_project_workflow_defs_for_project(db, project_id)
    node_labels = {d.node_key: d.label for d in node_defs}

    buckets: dict[str, _MemberBucket] = {
        user.id: _MemberBucket() for _, user in member_rows
    }

    for task, req, progress in task_rows:
        assignee_id = task.assignee_id
        if not assignee_id:
            continue
        if not _is_fully_scheduled(task) and _skip_unscheduled_for_node_state(progress):
            continue
        item = _build_task_item(task, req, node_labels, req_task_counts)
        _append_item_to_bucket(buckets, assignee_id, item, task, range_start, range_end)

    for link, bug in bug_link_rows:
        if not _is_schedule_participating(link):
            continue
        item = _build_bug_item(link, bug)
        _append_item_to_bucket(buckets, link.user_id, item, link, range_start, range_end)

    members_out: list[MemberScheduleRowOut] = []

    for _member, user in member_rows:
        uid = user.id
        bucket = buckets.get(uid, _MemberBucket())
        member_points = sum(_estimate_value(i.estimate_points) for i in bucket.scheduled)
        members_out.append(
            MemberScheduleRowOut(
                user_id=uid,
                name=(user.name or "").strip() or user.email or uid,
                scheduled_count=len(bucket.scheduled),
                total_estimate_points=member_points,
                unscheduled_count=len(bucket.unscheduled),
                scheduled_items=bucket.scheduled,
                unscheduled_items=bucket.unscheduled,
            )
        )

    already_added = {m.user_id for m in members_out}
    extra_uids = [uid for uid in buckets if uid not in already_added]
    extra_users: dict[str, User] = {}
    if extra_uids:
        extra_user_rows = await db.execute(select(User).where(User.id.in_(extra_uids)))
        extra_users = {u.id: u for u in extra_user_rows.scalars().all()}

    for uid, bucket in buckets.items():
        if uid in already_added:
            continue
        user = extra_users.get(uid)
        name = (user.name or "").strip() if user else uid
        if user and not name:
            name = user.email or uid
        member_points = sum(_estimate_value(i.estimate_points) for i in bucket.scheduled)
        members_out.append(
            MemberScheduleRowOut(
                user_id=uid,
                name=name,
                scheduled_count=len(bucket.scheduled),
                total_estimate_points=member_points,
                unscheduled_count=len(bucket.unscheduled),
                scheduled_items=bucket.scheduled,
                unscheduled_items=bucket.unscheduled,
            )
        )

    members_out.sort(key=lambda m: m.name)

    return MemberScheduleOut(
        range_start=range_start,
        range_end=range_end,
        members=members_out,
    )
