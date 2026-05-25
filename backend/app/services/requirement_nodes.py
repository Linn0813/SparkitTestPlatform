from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.requirement_status import requirement_status_label
from app.constants.requirement_status_rules import StatusRuleLike, lane_match_requirements
from app.services.requirement_status_rules import default_status_rule_likes, load_status_rules_for_derive
from app.models.requirement import (
    Requirement,
    RequirementNodeProgress,
    RequirementNodeState,
    RequirementStatus,
    RequirementType,
)
from app.models.template import RequirementWorkflowNodeDef
from app.services.requirement_activity import log_requirement_activity
from app.services.requirement_workflow import build_lanes

NodeMap = dict[str, RequirementNodeProgress]


class RequirementNodeError(ValueError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _node_state(node: RequirementNodeProgress | None) -> RequirementNodeState:
    if node is None:
        return RequirementNodeState.pending
    return node.state


def _is_enabled(node: RequirementNodeProgress | None) -> bool:
    if node is None:
        return False
    return bool(node.enabled)


def _is_done(node: RequirementNodeProgress | None) -> bool:
    if node is None:
        return True
    if not node.enabled:
        return True
    return _node_state(node) in (RequirementNodeState.completed, RequirementNodeState.skipped)


def _enabled_nodes_in_lane(
    lane: list[RequirementWorkflowNodeDef], nodes: NodeMap
) -> list[RequirementWorkflowNodeDef]:
    return [d for d in lane if _is_enabled(nodes.get(d.node_key))]


def _lane_done(lane: list[RequirementWorkflowNodeDef], nodes: NodeMap) -> bool:
    enabled = _enabled_nodes_in_lane(lane, nodes)
    if not enabled:
        return True
    return all(_is_done(nodes.get(d.node_key)) for d in enabled)


def _lane_gate_nodes(
    lane: list[RequirementWorkflowNodeDef], nodes: NodeMap
) -> list[RequirementWorkflowNodeDef]:
    return [d for d in _enabled_nodes_in_lane(lane, nodes) if d.blocks_lane_gate]


def _lane_gate_done(lane: list[RequirementWorkflowNodeDef], nodes: NodeMap) -> bool:
    gate_nodes = _lane_gate_nodes(lane, nodes)
    if not gate_nodes:
        return True
    return all(_is_done(nodes.get(d.node_key)) for d in gate_nodes)


def _lane_has_in_progress(lane: list[RequirementWorkflowNodeDef], nodes: NodeMap) -> bool:
    for d in _enabled_nodes_in_lane(lane, nodes):
        if _node_state(nodes.get(d.node_key)) == RequirementNodeState.in_progress:
            return True
    return False


def _min_lane_number(defs: list[RequirementWorkflowNodeDef], node_key: str) -> int | None:
    from app.services.requirement_workflow import def_lane_indexes

    for d in defs:
        if d.node_key == node_key:
            return min(def_lane_indexes(d))
    return None


def _find_lane_list_index(
    lanes: list[list[RequirementWorkflowNodeDef]],
    defs: list[RequirementWorkflowNodeDef],
    node_key: str,
) -> int | None:
    min_lane = _min_lane_number(defs, node_key)
    if min_lane is None:
        return None
    from app.services.requirement_workflow import def_lane_indexes

    sorted_lane_nums = sorted({li for d in defs for li in def_lane_indexes(d)})
    try:
        return sorted_lane_nums.index(min_lane)
    except ValueError:
        return None


def _node_completed(nodes: NodeMap, node_key: str) -> bool:
    node = nodes.get(node_key)
    return bool(node and node.enabled and _node_state(node) == RequirementNodeState.completed)


def _node_incomplete(nodes: NodeMap, node_key: str) -> bool:
    node = nodes.get(node_key)
    if not node or not node.enabled:
        return False
    return _node_state(node) not in (
        RequirementNodeState.completed,
        RequirementNodeState.skipped,
    )


def _match_status_rule(
    req: Requirement,
    nodes: NodeMap,
    lane: list[RequirementWorkflowNodeDef] | None,
    rule: StatusRuleLike,
) -> bool:
    if rule.trigger_type == "status_hold":
        return req.status.value == rule.status

    if rule.trigger_type == "node_completed":
        if not rule.node_keys:
            return False
        return all(_node_completed(nodes, k) for k in rule.node_keys)

    if rule.trigger_type != "lane" or lane is None:
        return False

    keys = {d.node_key for d in lane}
    if not (keys & set(rule.node_keys)):
        return False

    require_completed, require_incomplete = lane_match_requirements(rule.status, rule.node_keys)
    if require_incomplete and not any(_node_incomplete(nodes, k) for k in require_incomplete):
        return False
    if require_completed and not all(_node_completed(nodes, k) for k in require_completed):
        return False

    return True


def derive_requirement_status(
    req: Requirement,
    nodes: NodeMap,
    defs: list[RequirementWorkflowNodeDef],
    *,
    rules: list[StatusRuleLike] | None = None,
) -> RequirementStatus:
    # 评审打回：不进入可配置映射表，保持不通过直至重新打开
    if req.status == RequirementStatus.rejected:
        return RequirementStatus.rejected

    rule_list = rules or default_status_rule_likes()

    lanes = build_lanes(defs)
    if not lanes:
        return RequirementStatus.draft

    current_lane: list[RequirementWorkflowNodeDef] | None = None
    for i, lane in enumerate(lanes):
        if not _enabled_nodes_in_lane(lane, nodes):
            continue
        if i > 0 and not all(_lane_gate_done(prev, nodes) for prev in lanes[:i]):
            current_lane = lane
            break
        if not _lane_gate_done(lane, nodes):
            current_lane = lane
            break
        if _lane_has_in_progress(lane, nodes):
            later_active = any(
                _lane_has_in_progress(lanes[j], nodes)
                for j in range(i + 1, len(lanes))
                if _enabled_nodes_in_lane(lanes[j], nodes)
            )
            if later_active:
                continue
            current_lane = lane
            break
        if not _lane_done(lane, nodes):
            current_lane = lane
            break

    for rule in sorted(rule_list, key=lambda r: (r.sort, r.status)):
        if _match_status_rule(req, nodes, current_lane, rule):
            return RequirementStatus(rule.status)

    return RequirementStatus.draft


def _assert_previous_lane_gate(
    nodes: NodeMap,
    defs: list[RequirementWorkflowNodeDef],
    node_key: str,
) -> None:
    lanes = build_lanes(defs)
    lane_idx = _find_lane_list_index(lanes, defs, node_key)
    if lane_idx is None:
        raise RequirementNodeError("未知节点")
    if lane_idx == 0:
        return
    for prev in lanes[:lane_idx]:
        if not _lane_gate_done(prev, nodes):
            raise RequirementNodeError("请先完成上一阶段节点")


def _can_start_node(
    req: Requirement,
    nodes: NodeMap,
    defs: list[RequirementWorkflowNodeDef],
    node_key: str,
) -> None:
    node = nodes.get(node_key)
    if not node or not node.enabled:
        raise RequirementNodeError("节点未启用或不存在")

    state = _node_state(node)
    if state != RequirementNodeState.pending:
        raise RequirementNodeError("节点当前不可开始")

    _assert_previous_lane_gate(nodes, defs, node_key)


def auto_start_ready_nodes(
    req: Requirement,
    nodes: NodeMap,
    defs: list[RequirementWorkflowNodeDef],
    *,
    actor_id: str | None = None,
) -> list[str]:
    """前置阶段 gate 已满足时，将 pending 节点自动置为进行中。"""
    if req.status in (RequirementStatus.rejected, RequirementStatus.closed):
        return []

    now = _utcnow()
    started: list[str] = []
    for d in defs:
        key = d.node_key
        node = nodes.get(key)
        if not node or not node.enabled:
            continue
        if _node_state(node) != RequirementNodeState.pending:
            continue
        try:
            _assert_previous_lane_gate(nodes, defs, key)
        except RequirementNodeError:
            continue
        node.state = RequirementNodeState.in_progress
        if not node.started_at:
            node.started_at = now
        if actor_id:
            node.operator_id = actor_id
        started.append(key)
    return started


def _can_complete_node(
    nodes: NodeMap,
    defs: list[RequirementWorkflowNodeDef],
    node_key: str,
) -> None:
    node = nodes.get(node_key)
    if not node or not node.enabled:
        raise RequirementNodeError("节点未启用或不存在")
    state = _node_state(node)
    if state not in (RequirementNodeState.pending, RequirementNodeState.in_progress):
        raise RequirementNodeError("节点当前不可完成")
    _assert_previous_lane_gate(nodes, defs, node_key)


def _can_skip_node(
    req: Requirement,
    nodes: NodeMap,
    defs: list[RequirementWorkflowNodeDef],
    node_key: str,
) -> None:
    if req.req_type != RequirementType.tech_optimization:
        raise RequirementNodeError("仅技术优化类需求可跳过节点")
    node = nodes.get(node_key)
    if not node or not node.enabled:
        raise RequirementNodeError("节点未启用或不存在")
    if _node_state(node) != RequirementNodeState.pending:
        raise RequirementNodeError("节点当前不可跳过")
    _can_start_node(req, nodes, defs, node_key)


async def apply_node_action(
    db: AsyncSession,
    req: Requirement,
    nodes: NodeMap,
    defs: list[RequirementWorkflowNodeDef],
    *,
    node_key: str,
    action: str,
    actor_id: str,
) -> RequirementStatus:
    if req.status == RequirementStatus.rejected and action != "reopen":
        raise RequirementNodeError("需求已打回，请先重新打开")
    if req.status == RequirementStatus.closed:
        raise RequirementNodeError("需求已关闭，请先重新打开")

    node = nodes.get(node_key)
    if not node:
        raise RequirementNodeError("节点不存在")

    from app.constants.requirement_nodes import requirement_node_label

    now = _utcnow()
    old_status = req.status

    auto_start_ready_nodes(req, nodes, defs, actor_id=actor_id)

    if action == "start":
        _can_start_node(req, nodes, defs, node_key)
        node.state = RequirementNodeState.in_progress
        node.started_at = now
        node.operator_id = actor_id
        summary = f"开始节点：{requirement_node_label(node_key)}"
    elif action == "complete":
        _can_complete_node(nodes, defs, node_key)
        node.state = RequirementNodeState.completed
        node.completed_at = now
        node.operator_id = actor_id
        summary = f"完成节点：{requirement_node_label(node_key)}"
    elif action == "skip":
        _can_skip_node(req, nodes, defs, node_key)
        node.state = RequirementNodeState.skipped
        node.completed_at = now
        node.operator_id = actor_id
        summary = f"跳过节点：{requirement_node_label(node_key)}"
    elif action == "reopen":
        if not node.enabled:
            raise RequirementNodeError("节点未启用")
        if node.state not in (
            RequirementNodeState.completed,
            RequirementNodeState.skipped,
            RequirementNodeState.in_progress,
        ):
            raise RequirementNodeError("节点当前不可重开")
        node.state = RequirementNodeState.pending
        node.started_at = None
        node.completed_at = None
        node.operator_id = actor_id
        summary = f"重开节点：{requirement_node_label(node_key)}"
    elif action == "reject":
        if node_key != "req_review":
            raise RequirementNodeError("仅需求评审可打回")
        if not node.enabled or _node_state(node) != RequirementNodeState.in_progress:
            raise RequirementNodeError("评审进行中才可打回")
        node.state = RequirementNodeState.pending
        node.started_at = None
        node.completed_at = None
        req.status = RequirementStatus.rejected
        await log_requirement_activity(
            db,
            requirement_id=req.id,
            actor_id=actor_id,
            action_type="reject",
            summary="需求评审不通过",
            detail={"node_key": node_key},
        )
        return RequirementStatus.rejected
    else:
        raise RequirementNodeError("未知操作")

    await db.flush()
    rules = await load_status_rules_for_derive(db, req.project_id)
    new_status = derive_requirement_status(req, nodes, defs, rules=rules)
    req.status = new_status

    await log_requirement_activity(
        db,
        requirement_id=req.id,
        actor_id=actor_id,
        action_type=f"node_{action}",
        summary=summary,
        detail={"node_key": node_key, "action": action},
    )

    if old_status != new_status and old_status != RequirementStatus.rejected:
        await log_requirement_activity(
            db,
            requirement_id=req.id,
            actor_id=actor_id,
            action_type="status_change",
            summary=f"状态变更：{requirement_status_label(old_status.value)} → {requirement_status_label(new_status.value)}",
            detail={"from_status": old_status.value, "to_status": new_status.value},
        )

    return new_status


async def close_requirement(
    db: AsyncSession,
    req: Requirement,
    *,
    actor_id: str,
) -> RequirementStatus:
    if req.status == RequirementStatus.closed:
        raise RequirementNodeError("需求已关闭")
    if req.status == RequirementStatus.rejected:
        raise RequirementNodeError("需求已打回，无法关闭")
    if req.status == RequirementStatus.released:
        raise RequirementNodeError("需求已发版，无法关闭")

    req.status = RequirementStatus.closed
    await db.flush()
    await log_requirement_activity(
        db,
        requirement_id=req.id,
        actor_id=actor_id,
        action_type="close",
        summary="关闭了需求",
    )
    return RequirementStatus.closed


async def reopen_from_closed(
    db: AsyncSession,
    req: Requirement,
    nodes: NodeMap,
    defs: list[RequirementWorkflowNodeDef],
    *,
    actor_id: str,
) -> RequirementStatus:
    if req.status != RequirementStatus.closed:
        raise RequirementNodeError("需求未处于已关闭状态")

    req.status = RequirementStatus.draft
    await db.flush()
    rules = await load_status_rules_for_derive(db, req.project_id)
    new_status = derive_requirement_status(req, nodes, defs, rules=rules)
    req.status = new_status
    await db.flush()

    await log_requirement_activity(
        db,
        requirement_id=req.id,
        actor_id=actor_id,
        action_type="reopen_closed",
        summary="重新打开了需求（已关闭后）",
    )
    return new_status


async def reopen_from_rejected(
    db: AsyncSession,
    req: Requirement,
    nodes: NodeMap,
    defs: list[RequirementWorkflowNodeDef],
    *,
    actor_id: str,
) -> RequirementStatus:
    if req.status != RequirementStatus.rejected:
        raise RequirementNodeError("需求未处于不通过状态")

    req.status = RequirementStatus.draft
    lanes = build_lanes(defs)
    if lanes:
        first_lane_keys = {d.node_key for d in lanes[0]}
        for key in first_lane_keys:
            node = nodes.get(key)
            if node and node.enabled and node.state != RequirementNodeState.pending:
                node.state = RequirementNodeState.pending
                node.started_at = None
                node.completed_at = None
        review = nodes.get("req_review")
        if review and review.enabled and review.state != RequirementNodeState.pending:
            review.state = RequirementNodeState.pending
            review.started_at = None
            review.completed_at = None

    rules = await load_status_rules_for_derive(db, req.project_id)
    new_status = derive_requirement_status(req, nodes, defs, rules=rules)
    req.status = new_status

    await log_requirement_activity(
        db,
        requirement_id=req.id,
        actor_id=actor_id,
        action_type="reopen_rejected",
        summary="重新打开需求（评审不通过后）",
    )
    return new_status


async def update_requirement_enabled_nodes(
    db: AsyncSession,
    req: Requirement,
    nodes: NodeMap,
    defs: list[RequirementWorkflowNodeDef],
    enabled_map: dict[str, bool],
    *,
    actor_id: str,
) -> RequirementStatus:
    def_by_key = {d.node_key: d for d in defs}

    for key, enabled in enabled_map.items():
        if key not in def_by_key:
            raise RequirementNodeError(f"未知节点: {key}")

    for key, enabled in enabled_map.items():
        node = nodes.get(key)
        if not node:
            node = RequirementNodeProgress(
                requirement_id=req.id,
                node_key=key,
                state=RequirementNodeState.pending,
                enabled=enabled,
            )
            db.add(node)
            nodes[key] = node
        else:
            node.enabled = enabled
            if not enabled:
                node.state = RequirementNodeState.skipped
                node.started_at = None
                node.completed_at = None
            elif node.state == RequirementNodeState.skipped:
                node.state = RequirementNodeState.pending

    await db.flush()
    rules = await load_status_rules_for_derive(db, req.project_id)
    new_status = derive_requirement_status(req, nodes, defs, rules=rules)
    req.status = new_status
    await log_requirement_activity(
        db,
        requirement_id=req.id,
        actor_id=actor_id,
        action_type="workflow_enabled",
        summary="更新了工作流节点启用配置",
        detail={"enabled": enabled_map},
    )
    return new_status


async def ensure_requirement_nodes_auto_started(
    db: AsyncSession,
    req: Requirement,
    *,
    actor_id: str | None = None,
) -> list[str]:
    from app.services.requirement_workflow import load_project_workflow_defs

    defs = await load_project_workflow_defs(db, req.project_id)
    nodes = await load_node_map(db, req.id)
    started = auto_start_ready_nodes(req, nodes, defs, actor_id=actor_id)
    if not started:
        return []
    await db.flush()
    rules = await load_status_rules_for_derive(db, req.project_id)
    req.status = derive_requirement_status(req, nodes, defs, rules=rules)
    await db.flush()
    return started


async def sync_requirement_status_from_workflow(
    db: AsyncSession,
    req: Requirement,
    *,
    actor_id: str | None = None,
    log_activity: bool = True,
) -> tuple[RequirementStatus, bool]:
    from app.services.requirement_workflow import load_project_workflow_defs

    nodes = await load_node_map(db, req.id)
    defs = await load_project_workflow_defs(db, req.project_id)
    auto_start_ready_nodes(req, nodes, defs, actor_id=actor_id)
    await db.flush()
    rules = await load_status_rules_for_derive(db, req.project_id)
    old_status = req.status
    new_status = derive_requirement_status(req, nodes, defs, rules=rules)
    if new_status == old_status:
        return new_status, False

    req.status = new_status
    await db.flush()

    if log_activity and actor_id:
        await log_requirement_activity(
            db,
            requirement_id=req.id,
            actor_id=actor_id,
            action_type="status_sync",
            summary=(
                f"按最新规则刷新状态：{requirement_status_label(old_status.value)}"
                f" → {requirement_status_label(new_status.value)}"
            ),
            detail={"from_status": old_status.value, "to_status": new_status.value},
        )
    return new_status, True


async def sync_project_requirement_statuses(
    db: AsyncSession,
    project_id: str,
    *,
    actor_id: str | None = None,
) -> int:
    from sqlalchemy import select

    result = await db.execute(select(Requirement).where(Requirement.project_id == project_id))
    updated = 0
    for req in result.scalars().all():
        _, changed = await sync_requirement_status_from_workflow(
            db, req, actor_id=actor_id, log_activity=bool(actor_id)
        )
        if changed:
            updated += 1
    return updated


async def load_node_map(db: AsyncSession, requirement_id: str) -> NodeMap:
    from sqlalchemy import select

    result = await db.execute(
        select(RequirementNodeProgress).where(RequirementNodeProgress.requirement_id == requirement_id)
    )
    return {r.node_key: r for r in result.scalars().all()}
