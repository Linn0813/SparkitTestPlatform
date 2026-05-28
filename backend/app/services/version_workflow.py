from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.version_nodes import (
    VERSION_NODE_DEPENDENTS,
    VERSION_NODE_KEYS,
    VERSION_NODE_LABELS,
    VERSION_NODE_PREREQUISITES,
)
from app.models.project_version import ProjectVersion
from app.models.version_workflow import VersionNodeProgress, VersionNodeState, VersionStatus


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


def compute_version_status(nodes: dict[str, VersionNodeProgress]) -> VersionStatus:
    if _is_completed(nodes.get("live")):
        return VersionStatus.ended
    if _is_completed(nodes.get("release_verification")):
        return VersionStatus.reviewing
    if _is_completed(nodes.get("development")):
        return VersionStatus.releasing
    if _is_completed(nodes.get("planning")):
        return VersionStatus.developing
    return VersionStatus.planning


async def sync_version_status(version: ProjectVersion, nodes: dict[str, VersionNodeProgress]) -> None:
    version.status = compute_version_status(nodes).value


async def init_version_workflow(db: AsyncSession, version_id: str) -> list[VersionNodeProgress]:
    rows: list[VersionNodeProgress] = []
    for key in VERSION_NODE_KEYS:
        row = VersionNodeProgress(
            version_id=version_id,
            node_key=key,
            state=VersionNodeState.pending.value,
        )
        db.add(row)
        rows.append(row)
    await db.flush()
    return rows


def _check_prerequisites(nodes: dict[str, VersionNodeProgress], node_key: str) -> None:
    for prereq in VERSION_NODE_PREREQUISITES.get(node_key, ()):
        if not _is_completed(nodes.get(prereq)):
            label = VERSION_NODE_LABELS.get(prereq, prereq)
            raise VersionWorkflowError(f"请先完成：{label}")


async def complete_version_node(
    db: AsyncSession,
    version: ProjectVersion,
    node_key: str,
    operator_id: str,
) -> dict[str, VersionNodeProgress]:
    if node_key not in VERSION_NODE_KEYS:
        raise VersionWorkflowError("未知节点")

    nodes = await load_version_nodes(db, version.id)
    node = nodes.get(node_key)
    if not node:
        raise VersionWorkflowError("节点不存在")
    if node.state == VersionNodeState.completed.value:
        raise VersionWorkflowError("节点已完成")

    _check_prerequisites(nodes, node_key)

    node.state = VersionNodeState.completed.value
    node.completed_at = _utcnow()
    node.operator_id = operator_id

    if node_key == "live" and version.released_at is None:
        version.released_at = date.today()

    await sync_version_status(version, nodes)
    await db.flush()
    return nodes


async def reopen_version_node(
    db: AsyncSession,
    version: ProjectVersion,
    node_key: str,
) -> dict[str, VersionNodeProgress]:
    if node_key not in VERSION_NODE_KEYS:
        raise VersionWorkflowError("未知节点")

    nodes = await load_version_nodes(db, version.id)
    node = nodes.get(node_key)
    if not node:
        raise VersionWorkflowError("节点不存在")
    if node.state != VersionNodeState.completed.value:
        raise VersionWorkflowError("节点未完成，无法重开")

    for dep_key in VERSION_NODE_DEPENDENTS.get(node_key, ()):
        dep = nodes.get(dep_key)
        if dep and dep.state == VersionNodeState.completed.value:
            dep.state = VersionNodeState.pending.value
            dep.completed_at = None
            dep.operator_id = None

    await sync_version_status(version, nodes)
    await db.flush()
    return nodes
