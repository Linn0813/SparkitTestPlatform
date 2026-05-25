from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.requirement import Requirement, RequirementNodeProgress, RequirementNodeTask
from app.models.template import RequirementWorkflowNodeDef


class RequirementNodeTaskError(ValueError):
    pass


def aggregate_node_planned_schedule(
    tasks: list[RequirementNodeTask],
) -> tuple[Optional[date], Optional[date]]:
    starts = [t.scheduled_start for t in tasks if t.scheduled_start]
    ends = [t.scheduled_end for t in tasks if t.scheduled_end]
    planned_start = min(starts) if starts else None
    planned_end = max(ends) if ends else None
    return planned_start, planned_end


def first_assignee_for_role(requirement: Requirement, role_key: str) -> Optional[str]:
    from app.services.requirement_serializers import normalize_role_assignee_ids

    ids = normalize_role_assignee_ids(requirement).get(role_key) or []
    return ids[0] if ids else None


def sync_role_assignees_from_tasks(requirement: Requirement, all_tasks: list[RequirementNodeTask]) -> None:
    from app.services.requirement_serializers import ROLE_KEY_TO_ID_FIELD, normalize_role_assignee_ids

    existing = normalize_role_assignee_ids(requirement)
    by_role: dict[str, list[str]] = {k: list(v) for k, v in existing.items()}
    roles_in_tasks = {t.role_key for t in all_tasks}
    for role_key in roles_in_tasks:
        assignees = [
            uid
            for uid in dict.fromkeys(
                t.assignee_id for t in all_tasks if t.role_key == role_key and t.assignee_id
            )
        ]
        if assignees:
            by_role[role_key] = assignees
    requirement.role_assignee_ids = by_role
    for role_key, field in ROLE_KEY_TO_ID_FIELD.items():
        role_ids = by_role.get(role_key) or []
        setattr(requirement, field, role_ids[0] if role_ids else None)


async def fill_empty_task_assignees_from_requirement(
    db: AsyncSession, requirement: Requirement
) -> bool:
    tasks = await load_tasks_for_requirement(db, requirement.id)
    changed = False
    for task in tasks:
        if task.assignee_id:
            continue
        uid = first_assignee_for_role(requirement, task.role_key)
        if uid:
            task.assignee_id = uid
            changed = True
    if changed:
        await db.flush()
    return changed


async def load_tasks_for_requirement(
    db: AsyncSession, requirement_id: str
) -> list[RequirementNodeTask]:
    result = await db.execute(
        select(RequirementNodeTask)
        .where(RequirementNodeTask.requirement_id == requirement_id)
        .order_by(RequirementNodeTask.node_key, RequirementNodeTask.sort, RequirementNodeTask.created_at)
    )
    return list(result.scalars().all())


async def _next_task_sort(db: AsyncSession, requirement_id: str, node_key: str) -> int:
    result = await db.execute(
        select(func.max(RequirementNodeTask.sort)).where(
            RequirementNodeTask.requirement_id == requirement_id,
            RequirementNodeTask.node_key == node_key,
        )
    )
    return (result.scalar() or -1) + 1


def _validate_schedule(start: Optional[date], end: Optional[date]) -> None:
    if start and end and end < start:
        raise RequirementNodeTaskError("排期结束不能早于开始")


def validate_task_role_key(role_key: str, node_def: RequirementWorkflowNodeDef) -> None:
    if role_key not in (node_def.role_keys or []):
        raise RequirementNodeTaskError(f"角色 {role_key} 不属于该节点")


async def seed_default_tasks_for_requirement(
    db: AsyncSession,
    req: Requirement,
    progress_rows: list[RequirementNodeProgress],
    def_by_key: dict[str, RequirementWorkflowNodeDef],
    *,
    only_if_empty: bool = False,
) -> None:
    if only_if_empty:
        existing = await db.execute(
            select(func.count())
            .select_from(RequirementNodeTask)
            .where(RequirementNodeTask.requirement_id == req.id)
        )
        if (existing.scalar() or 0) > 0:
            return

    for progress in progress_rows:
        node_def = def_by_key.get(progress.node_key)
        if not node_def or not node_def.role_keys:
            continue
        role_key = node_def.role_keys[0]
        db.add(
            RequirementNodeTask(
                requirement_id=req.id,
                node_key=progress.node_key,
                title=node_def.label,
                role_key=role_key,
                assignee_id=first_assignee_for_role(req, role_key),
                sort=0,
            )
        )
    await db.flush()


async def seed_default_tasks_from_defs(
    db: AsyncSession,
    req: Requirement,
    defs: list[RequirementWorkflowNodeDef],
) -> None:
    for d in defs:
        if not d.role_keys:
            continue
        role_key = d.role_keys[0]
        db.add(
            RequirementNodeTask(
                requirement_id=req.id,
                node_key=d.node_key,
                title=d.label,
                role_key=role_key,
                assignee_id=first_assignee_for_role(req, role_key),
                sort=0,
            )
        )
    await db.flush()


async def get_node_def_or_raise(
    db: AsyncSession, project_id: str, node_key: str
) -> RequirementWorkflowNodeDef:
    from app.services.requirement_workflow import load_project_workflow_defs

    defs = await load_project_workflow_defs(db, project_id)
    for d in defs:
        if d.node_key == node_key:
            return d
    raise RequirementNodeTaskError("节点不存在")


async def get_task_or_raise(
    db: AsyncSession,
    requirement_id: str,
    node_key: str,
    task_id: str,
) -> RequirementNodeTask:
    task = await db.get(RequirementNodeTask, task_id)
    if not task or task.requirement_id != requirement_id or task.node_key != node_key:
        raise RequirementNodeTaskError("任务不存在")
    return task


async def apply_task_mutation_side_effects(
    db: AsyncSession, requirement: Requirement
) -> list[RequirementNodeTask]:
    tasks = await load_tasks_for_requirement(db, requirement.id)
    sync_role_assignees_from_tasks(requirement, tasks)
    await db.flush()
    return tasks


async def create_node_task(
    db: AsyncSession,
    requirement: Requirement,
    node_key: str,
    *,
    title: str,
    role_key: str,
    assignee_id: Optional[str] = None,
    estimate_points: Optional[float] = None,
    scheduled_start: Optional[date] = None,
    scheduled_end: Optional[date] = None,
) -> RequirementNodeTask:
    node_def = await get_node_def_or_raise(db, requirement.project_id, node_key)
    validate_task_role_key(role_key, node_def)
    _validate_schedule(scheduled_start, scheduled_end)
    if assignee_id is None:
        assignee_id = first_assignee_for_role(requirement, role_key)
    sort = await _next_task_sort(db, requirement.id, node_key)
    task = RequirementNodeTask(
        requirement_id=requirement.id,
        node_key=node_key,
        title=title.strip(),
        role_key=role_key,
        assignee_id=assignee_id,
        estimate_points=estimate_points,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        sort=sort,
    )
    db.add(task)
    await db.flush()
    await apply_task_mutation_side_effects(db, requirement)
    return task


async def update_node_task(
    db: AsyncSession,
    requirement: Requirement,
    task: RequirementNodeTask,
    *,
    title: Optional[str] = None,
    role_key: Optional[str] = None,
    assignee_id: Optional[str] = None,
    clear_assignee: bool = False,
    estimate_points: Optional[float] = None,
    clear_estimate: bool = False,
    scheduled_start: Optional[date] = None,
    scheduled_end: Optional[date] = None,
    clear_schedule: bool = False,
    sort: Optional[int] = None,
    fields_set: set[str] | None = None,
) -> RequirementNodeTask:
    node_def = await get_node_def_or_raise(db, requirement.project_id, task.node_key)
    fs = fields_set or set()
    if title is not None:
        task.title = title.strip()
    if role_key is not None:
        validate_task_role_key(role_key, node_def)
        task.role_key = role_key
    if "assignee_id" in fs:
        task.assignee_id = None if clear_assignee else assignee_id
    if "estimate_points" in fs:
        task.estimate_points = None if clear_estimate else estimate_points
    if "scheduled_start" in fs or "scheduled_end" in fs or clear_schedule:
        if clear_schedule:
            task.scheduled_start = None
            task.scheduled_end = None
        else:
            if "scheduled_start" in fs:
                task.scheduled_start = scheduled_start
            if "scheduled_end" in fs:
                task.scheduled_end = scheduled_end
    if sort is not None:
        task.sort = sort
    _validate_schedule(task.scheduled_start, task.scheduled_end)
    await db.flush()
    await apply_task_mutation_side_effects(db, requirement)
    return task


async def delete_node_task(
    db: AsyncSession,
    requirement: Requirement,
    task: RequirementNodeTask,
) -> None:
    await db.delete(task)
    await db.flush()
    await apply_task_mutation_side_effects(db, requirement)
