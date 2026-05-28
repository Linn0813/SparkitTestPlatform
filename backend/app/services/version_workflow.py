from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_version import ProjectVersion
from app.models.template import VersionWorkflowNodeDef
from app.models.version_workflow import VersionNodeProgress, VersionNodeState, VersionStatus
from app.services.version_status_derive import derive_version_status
from app.services.version_status_rules import default_version_status_rule_likes, load_status_rules_for_derive
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


def _is_in_progress(node: VersionNodeProgress | None) -> bool:
    return bool(node and node.state == VersionNodeState.in_progress.value)


def _prerequisites_met(
    nodes: dict[str, VersionNodeProgress],
    node_key: str,
    defs: list[VersionWorkflowNodeDef],
) -> bool:
    prereqs = compute_prerequisites(defs)
    return all(_is_completed(nodes.get(p)) for p in prereqs.get(node_key, ()))


def auto_start_ready_version_nodes(
    nodes: dict[str, VersionNodeProgress],
    defs: list[VersionWorkflowNodeDef],
    *,
    actor_id: str | None = None,
) -> list[str]:
    """前置节点均已完成后，将 pending 节点自动置为进行中。"""
    started: list[str] = []
    for d in defs:
        node = nodes.get(d.node_key)
        if not node or node.state != VersionNodeState.pending.value:
            continue
        if not _prerequisites_met(nodes, d.node_key, defs):
            continue
        node.state = VersionNodeState.in_progress.value
        if actor_id:
            node.operator_id = actor_id
        started.append(d.node_key)
    return started


def _revert_stale_in_progress_version_nodes(
    nodes: dict[str, VersionNodeProgress],
    defs: list[VersionWorkflowNodeDef],
) -> list[str]:
    """前置未满足时，将误保留的进行中节点回退为未开始。"""
    reverted: list[str] = []
    for d in defs:
        node = nodes.get(d.node_key)
        if not node or not _is_in_progress(node):
            continue
        if _prerequisites_met(nodes, d.node_key, defs):
            continue
        node.state = VersionNodeState.pending.value
        node.operator_id = None
        reverted.append(d.node_key)
    return reverted


def reconcile_version_workflow_nodes(
    nodes: dict[str, VersionNodeProgress],
    defs: list[VersionWorkflowNodeDef],
    *,
    actor_id: str | None = None,
) -> tuple[list[str], list[str]]:
    reverted = _revert_stale_in_progress_version_nodes(nodes, defs)
    started = auto_start_ready_version_nodes(nodes, defs, actor_id=actor_id)
    return started, reverted


async def _backfill_missing_version_nodes(
    db: AsyncSession,
    version_id: str,
    nodes: dict[str, VersionNodeProgress],
    defs: list[VersionWorkflowNodeDef],
) -> list[str]:
    added: list[str] = []
    for d in defs:
        if d.node_key in nodes:
            continue
        row = VersionNodeProgress(
            version_id=version_id,
            node_key=d.node_key,
            state=VersionNodeState.pending.value,
        )
        db.add(row)
        nodes[d.node_key] = row
        added.append(d.node_key)
    if added:
        await db.flush()
    return added


async def sync_version_progress_for_new_def(
    db: AsyncSession,
    project_id: str,
    version_type: str,
    node_key: str,
) -> None:
    defs = await load_project_version_workflow_defs(db, project_id, version_type)
    result = await db.execute(
        select(ProjectVersion).where(
            ProjectVersion.project_id == project_id,
            ProjectVersion.version_type == version_type,
        )
    )
    changed = False
    for ver in result.scalars().all():
        nodes = await load_version_nodes(db, ver.id)
        if node_key in nodes:
            continue
        row = VersionNodeProgress(
            version_id=ver.id,
            node_key=node_key,
            state=VersionNodeState.pending.value,
        )
        db.add(row)
        nodes[node_key] = row
        reconcile_version_workflow_nodes(nodes, defs)
        await sync_version_status(db, ver, nodes, defs)
        changed = True
    if changed:
        await db.flush()


async def ensure_version_workflow_nodes_started(
    db: AsyncSession,
    version: ProjectVersion,
    *,
    actor_id: str | None = None,
) -> tuple[list[str], list[str]]:
    defs = await load_project_version_workflow_defs(db, version.project_id, version.version_type)
    nodes = await load_version_nodes(db, version.id)
    backfilled = await _backfill_missing_version_nodes(db, version.id, nodes, defs)
    started, reverted = reconcile_version_workflow_nodes(nodes, defs, actor_id=actor_id)
    if backfilled or started or reverted:
        await sync_version_status(db, version, nodes, defs)
        await db.flush()
    return started, reverted


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
    """兼容旧调用：使用默认规则推导。"""
    version_type = defs[0].version_type if defs else "app_release"
    return derive_version_status(
        None,
        nodes,
        defs,
        rules=default_version_status_rule_likes(version_type),
    )


async def sync_version_status(
    db: AsyncSession,
    version: ProjectVersion,
    nodes: dict[str, VersionNodeProgress],
    defs: list[VersionWorkflowNodeDef],
) -> None:
    version_type = version.version_type or "app_release"
    rules = await load_status_rules_for_derive(db, version.project_id, version_type)
    version.status = derive_version_status(version, nodes, defs, rules=rules).value


async def sync_project_version_statuses(
    db: AsyncSession,
    project_id: str,
) -> int:
    result = await db.execute(
        select(ProjectVersion).where(ProjectVersion.project_id == project_id)
    )
    updated = 0
    for ver in result.scalars().all():
        defs = await load_project_version_workflow_defs(db, project_id, ver.version_type)
        nodes = await load_version_nodes(db, ver.id)
        old_status = ver.status
        await sync_version_status(db, ver, nodes, defs)
        if ver.status != old_status:
            updated += 1
    if updated:
        await db.flush()
    return updated


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


async def assert_version_workflow_node_deletable(
    db: AsyncSession,
    project_id: str,
    version_type: str,
    node_key: str,
) -> None:
    from sqlalchemy import func

    in_progress = await db.execute(
        select(func.count())
        .select_from(VersionNodeProgress)
        .join(ProjectVersion, ProjectVersion.id == VersionNodeProgress.version_id)
        .where(
            ProjectVersion.project_id == project_id,
            ProjectVersion.version_type == version_type,
            VersionNodeProgress.node_key == node_key,
            VersionNodeProgress.state == VersionNodeState.in_progress.value,
        )
    )
    if (in_progress.scalar() or 0) > 0:
        raise VersionWorkflowError("节点进行中，不可删除")


async def delete_version_node_progress_for_def(
    db: AsyncSession,
    project_id: str,
    version_type: str,
    node_key: str,
) -> None:
    from sqlalchemy import delete

    version_ids = select(ProjectVersion.id).where(
        ProjectVersion.project_id == project_id,
        ProjectVersion.version_type == version_type,
    )
    await db.execute(
        delete(VersionNodeProgress).where(
            VersionNodeProgress.node_key == node_key,
            VersionNodeProgress.version_id.in_(version_ids),
        )
    )


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
    if node.state not in (
        VersionNodeState.pending.value,
        VersionNodeState.in_progress.value,
    ):
        raise VersionWorkflowError("节点当前不可完成")

    _check_prerequisites(nodes, node_key, defs)

    node.state = VersionNodeState.completed.value
    node.completed_at = _utcnow()
    node.operator_id = operator_id

    if node_key == "live" and version.released_at is None:
        version.released_at = date.today()

    reconcile_version_workflow_nodes(nodes, defs, actor_id=operator_id)
    await sync_version_status(db, version, nodes, defs)
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
        if dep and dep.state in (
            VersionNodeState.completed.value,
            VersionNodeState.in_progress.value,
        ):
            dep.state = VersionNodeState.pending.value
            dep.completed_at = None
            dep.operator_id = None

    reconcile_version_workflow_nodes(nodes, defs)
    await sync_version_status(db, version, nodes, defs)
    await db.flush()
    return nodes


def sort_nodes_by_defs(
    nodes: list[VersionNodeProgress],
    defs: list[VersionWorkflowNodeDef],
) -> list[VersionNodeProgress]:
    order = ordered_node_keys(defs)
    by_key = {n.node_key: n for n in nodes}
    return [by_key[key] for key in order if key in by_key]
