from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.requirement import Requirement, RequirementNodeProgress, RequirementNodeState, RequirementType
from app.models.template import RequirementWorkflowNodeDef
from app.services.requirement_workflow_defaults import (
    DEFAULT_REQUIREMENT_WORKFLOW_NODES,
    TECH_OPTIMIZATION_DEFAULT_DISABLED_NODES,
)


def build_lanes(defs: list[RequirementWorkflowNodeDef]) -> list[list[RequirementWorkflowNodeDef]]:
    by_lane: dict[int, list[RequirementWorkflowNodeDef]] = defaultdict(list)
    for d in defs:
        for lane in def_lane_indexes(d):
            if d not in by_lane[lane]:
                by_lane[lane].append(d)
    return [by_lane[i] for i in sorted(by_lane.keys())]


def def_lane_indexes(d: RequirementWorkflowNodeDef) -> list[int]:
    if d.lane_indexes:
        return sorted(set(int(i) for i in d.lane_indexes))
    return [d.lane_index]


def sync_lane_fields(row: RequirementWorkflowNodeDef) -> None:
    indexes = def_lane_indexes(row)
    row.lane_indexes = indexes
    row.lane_index = indexes[0] if indexes else 0


def validate_lane_indexes(lane_indexes: list[int]) -> None:
    if not lane_indexes:
        raise ValueError("至少选择一个阶段列")
    if any(i < 0 for i in lane_indexes):
        raise ValueError("阶段列不能为负数")
    if len(lane_indexes) != len(set(lane_indexes)):
        raise ValueError("阶段列不能重复")


async def load_project_workflow_defs(
    db: AsyncSession, project_id: str
) -> list[RequirementWorkflowNodeDef]:
    result = await db.execute(
        select(RequirementWorkflowNodeDef)
        .where(RequirementWorkflowNodeDef.project_id == project_id)
        .order_by(RequirementWorkflowNodeDef.lane_index, RequirementWorkflowNodeDef.sort_in_lane)
    )
    return list(result.scalars().all())


async def ensure_project_workflow_defs(db: AsyncSession, project_id: str) -> list[RequirementWorkflowNodeDef]:
    existing = await load_project_workflow_defs(db, project_id)
    if existing:
        return existing
    rows: list[RequirementWorkflowNodeDef] = []
    for item in DEFAULT_REQUIREMENT_WORKFLOW_NODES:
        row = RequirementWorkflowNodeDef(project_id=project_id, **item)
        db.add(row)
        rows.append(row)
    await db.flush()
    return rows


def default_enabled_for_node(node_key: str, req_type: RequirementType) -> bool:
    if req_type == RequirementType.tech_optimization and node_key in TECH_OPTIMIZATION_DEFAULT_DISABLED_NODES:
        return False
    return True


def resolve_node_enabled(
    node_key: str,
    req_type: RequirementType,
    enabled_map: dict[str, bool] | None,
) -> bool:
    if enabled_map is not None and node_key in enabled_map:
        return bool(enabled_map[node_key])
    return default_enabled_for_node(node_key, req_type)


async def init_requirement_progress_from_defs(
    db: AsyncSession,
    req: Requirement,
    defs: list[RequirementWorkflowNodeDef],
    *,
    enabled_map: dict[str, bool] | None = None,
) -> None:
    for d in defs:
        enabled = resolve_node_enabled(d.node_key, req.req_type, enabled_map)
        state = RequirementNodeState.skipped if not enabled else RequirementNodeState.pending
        db.add(
            RequirementNodeProgress(
                requirement_id=req.id,
                node_key=d.node_key,
                state=state,
                enabled=enabled,
            )
        )
    await db.flush()


async def init_requirement_tasks_from_defs(
    db: AsyncSession,
    req: Requirement,
    defs: list[RequirementWorkflowNodeDef],
    *,
    enabled_map: dict[str, bool] | None = None,
) -> None:
    from app.services.requirement_node_tasks import seed_default_tasks_from_defs

    active = [
        d
        for d in defs
        if resolve_node_enabled(d.node_key, req.req_type, enabled_map)
    ]
    await seed_default_tasks_from_defs(db, req, active)


async def sync_progress_for_new_def(
    db: AsyncSession,
    project_id: str,
    node_key: str,
) -> None:
    from app.models.requirement import RequirementNodeTask
    from app.services.requirement_node_tasks import seed_default_tasks_for_requirement

    defs = await load_project_workflow_defs(db, project_id)
    node_def = next((d for d in defs if d.node_key == node_key), None)
    def_by_key = {node_key: node_def} if node_def else {}

    reqs = await db.execute(select(Requirement).where(Requirement.project_id == project_id))
    for req in reqs.scalars().all():
        existing = await db.execute(
            select(RequirementNodeProgress).where(
                RequirementNodeProgress.requirement_id == req.id,
                RequirementNodeProgress.node_key == node_key,
            )
        )
        if existing.scalar_one_or_none():
            continue
        progress = RequirementNodeProgress(
            requirement_id=req.id,
            node_key=node_key,
            state=RequirementNodeState.pending,
            enabled=False,
        )
        db.add(progress)
        await db.flush()
        if node_def and node_def.role_keys:
            task_exists = await db.execute(
                select(RequirementNodeTask.id).where(
                    RequirementNodeTask.requirement_id == req.id,
                    RequirementNodeTask.node_key == node_key,
                )
            )
            if task_exists.first() is None:
                await seed_default_tasks_for_requirement(
                    db, req, [progress], def_by_key, only_if_empty=False
                )
    await db.flush()


def new_custom_node_key() -> str:
    return f"custom_{uuid.uuid4().hex[:12]}"


def validate_role_keys(role_keys: list[str]) -> None:
    from app.constants.requirement_nodes import REQUIREMENT_ROLE_KEYS

    if not role_keys:
        return
    seen: set[str] = set()
    for role_key in role_keys:
        if role_key not in REQUIREMENT_ROLE_KEYS:
            raise ValueError(f"无效角色: {role_key}")
        if role_key in seen:
            raise ValueError(f"角色重复: {role_key}")
        seen.add(role_key)


async def validate_role_keys_for_project(
    db: AsyncSession, project_id: str, role_keys: list[str]
) -> None:
    from app.services.requirement_config import validate_role_keys_for_project as _validate

    await _validate(db, project_id, role_keys)


async def assert_workflow_node_deletable(db: AsyncSession, node_key: str) -> None:
    from sqlalchemy import func, select

    in_progress = await db.execute(
        select(func.count())
        .select_from(RequirementNodeProgress)
        .where(
            RequirementNodeProgress.node_key == node_key,
            RequirementNodeProgress.state == RequirementNodeState.in_progress,
        )
    )
    if (in_progress.scalar() or 0) > 0:
        raise ValueError("节点进行中，不可删除")
