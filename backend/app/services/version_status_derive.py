from __future__ import annotations

from app.constants.version_status_rules import (
    DEFAULT_VERSION_STATUS_RULES,
    VersionStatusRuleLike,
    version_lane_match_requirements,
)
from app.constants.version_types import REVIEW_NODE_KEYS
from app.models.project_version import ProjectVersion
from app.models.template import VersionWorkflowNodeDef
from app.models.version_workflow import VersionNodeProgress, VersionNodeState, VersionStatus
from app.services.version_workflow_defs import build_lanes

NodeMap = dict[str, VersionNodeProgress]


def _node_completed(nodes: NodeMap, key: str) -> bool:
    node = nodes.get(key)
    return bool(node and node.state == VersionNodeState.completed.value)


def _node_incomplete(nodes: NodeMap, key: str) -> bool:
    return not _node_completed(nodes, key)


def _lane_done(lane: list[VersionWorkflowNodeDef], nodes: NodeMap) -> bool:
    keys = [d.node_key for d in lane]
    if not keys:
        return True
    return all(_node_completed(nodes, k) for k in keys)


def _lane_has_in_progress(lane: list[VersionWorkflowNodeDef], nodes: NodeMap) -> bool:
    for d in lane:
        node = nodes.get(d.node_key)
        if node and node.state == VersionNodeState.in_progress.value:
            return True
    return False


def _nodes_in_defs(lane: list[VersionWorkflowNodeDef], nodes: NodeMap) -> bool:
    return any(d.node_key in nodes for d in lane)


def _rule_applicable(rule: VersionStatusRuleLike, defs: list[VersionWorkflowNodeDef]) -> bool:
    def_keys = {d.node_key for d in defs}
    if rule.trigger_type == "status_hold":
        return True
    if not rule.node_keys:
        return False
    return all(k in def_keys for k in rule.node_keys)


def _reviewing_rule_allowed(rule: VersionStatusRuleLike, defs: list[VersionWorkflowNodeDef]) -> bool:
    if rule.status != "reviewing" or rule.trigger_type != "node_completed":
        return True
    def_keys = {d.node_key for d in defs}
    return any(k in def_keys for k in REVIEW_NODE_KEYS)


def _match_status_rule(
    version: ProjectVersion | None,
    nodes: NodeMap,
    lane: list[VersionWorkflowNodeDef] | None,
    rule: VersionStatusRuleLike,
    defs: list[VersionWorkflowNodeDef],
) -> bool:
    if not _rule_applicable(rule, defs):
        return False
    if not _reviewing_rule_allowed(rule, defs):
        return False

    if rule.trigger_type == "status_hold":
        return bool(version and version.status == rule.status)

    if rule.trigger_type == "node_completed":
        if not rule.node_keys:
            return False
        return all(_node_completed(nodes, k) for k in rule.node_keys)

    if rule.trigger_type != "lane" or lane is None:
        return False

    keys = {d.node_key for d in lane}
    if not (keys & set(rule.node_keys)):
        return False

    require_completed, require_incomplete = version_lane_match_requirements(rule.status, rule.node_keys)
    if require_incomplete and not any(_node_incomplete(nodes, k) for k in require_incomplete):
        return False
    if require_completed and not all(_node_completed(nodes, k) for k in require_completed):
        return False

    return True


def derive_version_status(
    version: ProjectVersion | None,
    nodes: NodeMap,
    defs: list[VersionWorkflowNodeDef],
    *,
    rules: list[VersionStatusRuleLike] | None = None,
) -> VersionStatus:
    rule_list = rules or list(DEFAULT_VERSION_STATUS_RULES)

    lanes = build_lanes(defs)
    if not lanes:
        return VersionStatus.planning

    current_lane: list[VersionWorkflowNodeDef] | None = None
    for i, lane in enumerate(lanes):
        if not _nodes_in_defs(lane, nodes):
            continue
        if i > 0 and not all(_lane_done(prev, nodes) for prev in lanes[:i]):
            current_lane = lane
            break
        if not _lane_done(lane, nodes):
            current_lane = lane
            break
        if _lane_has_in_progress(lane, nodes):
            later_active = any(
                _lane_has_in_progress(lanes[j], nodes)
                for j in range(i + 1, len(lanes))
                if _nodes_in_defs(lanes[j], nodes)
            )
            if later_active:
                continue
            current_lane = lane
            break
        if not _lane_done(lane, nodes):
            current_lane = lane
            break

    for rule in sorted(rule_list, key=lambda r: (r.sort, r.status)):
        if _match_status_rule(version, nodes, current_lane, rule, defs):
            return VersionStatus(rule.status)

    return VersionStatus.planning
