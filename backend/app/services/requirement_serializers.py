from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.requirement_nodes import REQUIREMENT_NODE_ROLE_KEYS, requirement_node_label
from app.models.project import ProjectMember
from app.models.requirement import Requirement, RequirementNodeProgress, RequirementNodeState, RequirementNodeTask
from app.models.user import User
from app.schemas.requirement import RequirementNodeProgressOut, RequirementNodeTaskOut, RequirementOut, RequirementWorkflowOut
from app.schemas.user import UserOut
from app.schemas.version import VersionBrief
from app.services.requirement_nodes import load_node_map
from app.services.requirement_list_derived import (
    build_developers_out,
    collect_developer_user_ids,
    compute_dev_handoff_date,
)
from app.services.requirement_node_tasks import aggregate_node_planned_schedule, load_tasks_for_requirement
from app.services.requirement_workflow import def_lane_indexes, ensure_project_workflow_defs, load_project_workflow_defs

ROLE_KEY_TO_ID_FIELD = {
    "frontend_rd": "frontend_rd_id",
    "backend_rd": "backend_rd_id",
    "pm": "pm_id",
    "tech_owner": "tech_owner_id",
    "qa": "qa_id",
    "designer": "designer_id",
}


def normalize_role_assignee_ids(row: Requirement) -> dict[str, list[str]]:
    stored = row.role_assignee_ids if isinstance(row.role_assignee_ids, dict) else {}
    if stored:
        return {k: [uid for uid in v if uid] for k, v in stored.items() if v}
    result: dict[str, list[str]] = {}
    for role_key, field in ROLE_KEY_TO_ID_FIELD.items():
        uid = getattr(row, field)
        if uid:
            result[role_key] = [uid]
    return result


async def validate_requirement_role_user_ids(
    db: AsyncSession,
    project_id: str,
    user_ids: list[str | None],
) -> None:
    ids = {uid for uid in user_ids if uid}
    if not ids:
        return
    result = await db.execute(
        select(ProjectMember.user_id).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id.in_(ids),
        )
    )
    found = {row[0] for row in result.all()}
    missing = ids - found
    if missing:
        raise ValueError(f"用户不属于当前项目: {', '.join(sorted(missing))}")


async def build_node_task_outs(
    tasks: list[RequirementNodeTask], db: AsyncSession
) -> list[RequirementNodeTaskOut]:
    user_ids = {t.assignee_id for t in tasks if t.assignee_id}
    users_map: dict[str, UserOut] = {}
    if user_ids:
        result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users_map = {u.id: UserOut.model_validate(u) for u in result.scalars().all()}
    return [
        RequirementNodeTaskOut(
            id=t.id,
            requirement_id=t.requirement_id,
            node_key=t.node_key,
            title=t.title,
            role_key=t.role_key,
            assignee_id=t.assignee_id,
            assignee=users_map.get(t.assignee_id) if t.assignee_id else None,
            estimate_points=t.estimate_points,
            scheduled_start=t.scheduled_start,
            scheduled_end=t.scheduled_end,
            sort=t.sort,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in tasks
    ]


async def build_requirement_workflow_out(
    row: Requirement, db: AsyncSession, tasks: list[RequirementNodeTask] | None = None
) -> RequirementWorkflowOut:
    from app.schemas.requirement import RequirementWorkflowNodeDefOut

    if tasks is None:
        tasks = await load_tasks_for_requirement(db, row.id)
    tasks_by_node: dict[str, list[RequirementNodeTask]] = {}
    for t in tasks:
        tasks_by_node.setdefault(t.node_key, []).append(t)

    defs = await ensure_project_workflow_defs(db, row.project_id)
    node_map = await load_node_map(db, row.id)
    def_by_key = {d.node_key: d for d in defs}
    nodes: list[RequirementNodeProgressOut] = []
    for d in defs:
        progress = node_map.get(d.node_key)
        state = progress.state if progress else RequirementNodeState.pending
        enabled = progress.enabled if progress else True
        node_tasks = tasks_by_node.get(d.node_key, [])
        planned_start, planned_end = aggregate_node_planned_schedule(node_tasks)
        nodes.append(
            RequirementNodeProgressOut(
                node_key=d.node_key,
                label=d.label,
                state=state,
                role_keys=d.role_keys,
                enabled=enabled,
                lane_index=d.lane_index,
                lane_indexes=def_lane_indexes(d),
                blocks_lane_gate=bool(d.blocks_lane_gate),
                sort_in_lane=d.sort_in_lane,
                started_at=progress.started_at if progress else None,
                completed_at=progress.completed_at if progress else None,
                operator_id=progress.operator_id if progress else None,
                planned_schedule_start=planned_start,
                planned_schedule_end=planned_end,
            )
        )
    return RequirementWorkflowOut(
        defs=[RequirementWorkflowNodeDefOut.model_validate(d) for d in defs],
        nodes=nodes,
    )


async def requirement_out(row: Requirement, db: AsyncSession) -> RequirementOut:
    version = None
    if row.version_id:
        from app.models.project_version import ProjectVersion

        v = await db.get(ProjectVersion, row.version_id)
        if v:
            version = VersionBrief(id=v.id, num=v.num, name=v.name, released_at=v.released_at)

    user_ids = {
        uid
        for uid in (
            row.frontend_rd_id,
            row.backend_rd_id,
            row.pm_id,
            row.tech_owner_id,
            row.qa_id,
            row.designer_id,
        )
        if uid
    }
    role_assignee_ids = normalize_role_assignee_ids(row)
    for ids in role_assignee_ids.values():
        user_ids.update(uid for uid in ids if uid)
    users_map: dict[str, UserOut] = {}
    if user_ids:
        result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users_map = {u.id: UserOut.model_validate(u) for u in result.scalars().all()}

    tasks = await load_tasks_for_requirement(db, row.id)
    workflow = await build_requirement_workflow_out(row, db, tasks)
    node_tasks = await build_node_task_outs(tasks, db)
    dev_handoff_date = compute_dev_handoff_date(workflow.nodes)
    developer_ids = collect_developer_user_ids(row)
    developers = build_developers_out(developer_ids, users_map)

    return RequirementOut(
        id=row.id,
        project_id=row.project_id,
        num=row.num,
        title=row.title,
        external_url=row.external_url,
        version_id=row.version_id,
        version=version,
        priority=row.priority,
        req_type=row.req_type,
        status=row.status,
        frontend_rd_id=row.frontend_rd_id,
        backend_rd_id=row.backend_rd_id,
        pm_id=row.pm_id,
        tech_owner_id=row.tech_owner_id,
        qa_id=row.qa_id,
        designer_id=row.designer_id,
        role_assignee_ids=role_assignee_ids,
        custom_fields=row.custom_fields if isinstance(row.custom_fields, dict) else {},
        frontend_rd=users_map.get(row.frontend_rd_id) if row.frontend_rd_id else None,
        backend_rd=users_map.get(row.backend_rd_id) if row.backend_rd_id else None,
        pm=users_map.get(row.pm_id) if row.pm_id else None,
        tech_owner=users_map.get(row.tech_owner_id) if row.tech_owner_id else None,
        qa=users_map.get(row.qa_id) if row.qa_id else None,
        designer=users_map.get(row.designer_id) if row.designer_id else None,
        nodes=workflow.nodes,
        node_tasks=node_tasks,
        dev_handoff_date=dev_handoff_date,
        developers=developers,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
