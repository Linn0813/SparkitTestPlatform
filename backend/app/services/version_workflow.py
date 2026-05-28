from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.version_types import REVIEW_NODE_KEYS
from app.models.project_version import ProjectVersion
from app.models.template import VersionWorkflowNodeDef
from app.models.version_workflow import VersionNodeProgress, VersionNodeState, VersionStatus
from app.services.version_workflow_defs import (
    compute_prerequisites,
    compute_reopen_set,
    ensure_project_version_workflow_defs,
    label_for_node,
    load_project_version_workflow_defs,
    ordered_node_keys,
)


class VersionWorkflowError(ValueError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_completed(node: VersionNodeProgress | None) -> bool:
    return bool(node and node.state == VersionNodeState.completed.value)


async def load_version_nodes(
    db: AsyncSession, version_id: str
) -> dict[str, VersionNodeProgress]:
    result = await db.execute(
        select(VersionNodeProgress).where(VersionNodeProgress.version_id == version_id)
    )
    return {row.node_key: row for row in result.scalars().all()}


def compute_version_status(
    nodes: dict[str, VersionNodeProgress],
    defs: list[VersionWorkflowNodeDef],
) -> VersionStatus:
    node_keys = {d.node_key for d in defs}
    has_review_nodes = any(k in node_keys for k in REVIEW_NODE_KEYS)

    if _is_completed(nodes.get("live")):
        return VersionStatus.ended
    if has_review_nodes and _is_completed(nodes.get("release_verification")):
        return VersionStatus.reviewing
    if _is_completed(nodes.get("development")):
        return VersionStatus.releasing
    if _is_completed(nodes.get("planning")):
        return VersionStatus.developing
    return VersionStatus.planning


async def sync_version_status(
    version: ProjectVersion,
    nodes: dict[str, VersionNodeProgress],
    defs: list[VersionWorkflowNodeDef],
) -> None:
    version.status = compute_version_status(nodes, defs).value


async def init_version_workflow(
    db: AsyncSession,
    version_id: str,
    project_id: str,
    version_type: str,
) -> list[VersionNodeProgress]:
    defs = await ensure_project_version_workflow_defs(db, project_id, version_type)
    rows: list[VersionNodeProgress] = []
    for d in defs:
        row = VersionNodeProgress(
            version_id=version_id,
            node_key=d.node_key,
            state=VersionNodeState.pending.value,
        )
        db.add(row)
        rows.append(row)
    await db.flush()
    return rows


async def reset_version_workflow(
    db: AsyncSession,
    version: ProjectVersion,
) -> None:
    from sqlalchemy import delete

    await db.execute(
        delete(VersionNodeProgress).where(VersionNodeProgress.version_id == version.id)
    )
    version.status = VersionStatus.planning.value
    await init_version_workflow(db, version.id, version.project_id, version.version_type)
    await db.flush()


async def resync_version_workflow_on_type_change(
    db: AsyncSession,
    version: ProjectVersion,
    new_version_type: str,
) -> None:
    version.version_type = new_version_type
    await reset_version_workflow(db, version)


async def update_version_node_metadata(
    db: AsyncSession,
    version: ProjectVersion,
    node_key: str,
    updates: dict[str, object],
) -> VersionNodeProgress:
    defs = await load_project_version_workflow_defs(db, version.project_id, version.version_type)
    def_keys = {d.node_key for d in defs}
    if node_key not in def_keys:
        raise VersionWorkflowError("未知节点")

    nodes = await load_version_nodes(db, version.id)
    node = nodes.get(node_key)
    if not node:
        raise VersionWorkflowError("节点不存在")

    if "assignee_id" in updates:
        node.assignee_id = updates["assignee_id"]  # type: ignore[assignment]
    if "scheduled_start" in updates:
        node.scheduled_start = updates["scheduled_start"]  # type: ignore[assignment]
    if "scheduled_end" in updates:
        node.scheduled_end = updates["scheduled_end"]  # type: ignore[assignment]

    if (
        node.scheduled_start is not None
        and node.scheduled_end is not None
        and node.scheduled_end < node.scheduled_start
    ):
        raise VersionWorkflowError("排期结束日期不能早于开始日期")

    await db.flush()
    return node


def _check_prerequisites(
    nodes: dict[str, VersionNodeProgress],
    node_key: str,
    defs: list[VersionWorkflowNodeDef],
) -> None:
    prereqs = compute_prerequisites(defs)
    for prereq in prereqs.get(node_key, ()):
        if not _is_completed(nodes.get(prereq)):
            label = label_for_node(defs, prereq)
            raise VersionWorkflowError(f"请先完成：{label}")


async def complete_version_node(
    db: AsyncSession,
    version: ProjectVersion,
    node_key: str,
    operator_id: str,
) -> dict[str, VersionNodeProgress]:
    defs = await load_project_version_workflow_defs(db, version.project_id, version.version_type)
    def_keys = {d.node_key for d in defs}
    if node_key not in def_keys:
        raise VersionWorkflowError("未知节点")

    nodes = await load_version_nodes(db, version.id)
    node = nodes.get(node_key)
    if not node:
        raise VersionWorkflowError("节点不存在")
    if node.state == VersionNodeState.completed.value:
        raise VersionWorkflowError("节点已完成")

    _check_prerequisites(nodes, node_key, defs)

    node.state = VersionNodeState.completed.value
    node.completed_at = _utcnow()
    node.operator_id = operator_id

    if node_key == "live" and version.released_at is None:
        version.released_at = date.today()

    await sync_version_status(version, nodes, defs)
    await db.flush()
    return nodes


async def reopen_version_node(
    db: AsyncSession,
    version: ProjectVersion,
    node_key: str,
) -> dict[str, VersionNodeProgress]:
    defs = await load_project_version_workflow_defs(db, version.project_id, version.version_type)
    def_keys = {d.node_key for d in defs}
    if node_key not in def_keys:
        raise VersionWorkflowError("未知节点")

    nodes = await load_version_nodes(db, version.id)
    node = nodes.get(node_key)
    if not node:
        raise VersionWorkflowError("节点不存在")
    if node.state != VersionNodeState.completed.value:
        raise VersionWorkflowError("节点未完成，无法重开")

    for dep_key in compute_reopen_set(defs, node_key):
        dep = nodes.get(dep_key)
        if dep and dep.state == VersionNodeState.completed.value:
            dep.state = VersionNodeState.pending.value
            dep.completed_at = None
            dep.operator_id = None

    await sync_version_status(version, nodes, defs)
    await db.flush()
    return nodes


def sort_nodes_by_defs(
    nodes: list[VersionNodeProgress],
    defs: list[VersionWorkflowNodeDef],
) -> list[VersionNodeProgress]:
    order = ordered_node_keys(defs)
    by_key = {n.node_key: n for n in nodes}
    return [by_key[key] for key in order if key in by_key]
