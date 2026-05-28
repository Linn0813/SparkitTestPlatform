from __future__ import annotations

from app.constants.version_status_rules import (
    DEFAULT_VERSION_STATUS_RULES,
    VersionStatusRuleLike,
)
from app.models.template import VersionWorkflowNodeDef
from app.models.version_workflow import VersionNodeProgress, VersionNodeState, VersionStatus
from app.services.version_status_derive import derive_version_status
from app.services.version_status_rules import default_version_status_rule_likes
from app.services.version_workflow_defaults import (
    DEFAULT_APP_RELEASE_WORKFLOW_NODES,
    DEFAULT_HOTFIX_WORKFLOW_NODES,
)


def _nodes(states: dict[str, str]) -> dict[str, VersionNodeProgress]:
    result: dict[str, VersionNodeProgress] = {}
    for key, state in states.items():
        result[key] = VersionNodeProgress(
            version_id="ver-1",
            node_key=key,
            state=state,
        )
    return result


def _default_defs() -> list[VersionWorkflowNodeDef]:
    return [
        VersionWorkflowNodeDef(
            project_id="proj-1",
            version_type="app_release",
            **item,
        )
        for item in DEFAULT_APP_RELEASE_WORKFLOW_NODES
    ]


def _hotfix_defs() -> list[VersionWorkflowNodeDef]:
    return [
        VersionWorkflowNodeDef(
            project_id="proj-1",
            version_type="hotfix",
            **item,
        )
        for item in DEFAULT_HOTFIX_WORKFLOW_NODES
    ]


def _default_rules() -> list[VersionStatusRuleLike]:
    return default_version_status_rule_likes()


def test_derive_status_planning_default():
    defs = _default_defs()
    nodes = _nodes({k: VersionNodeState.pending.value for k in ("planning", "development")})
    assert derive_version_status(None, nodes, defs, rules=_default_rules()) == VersionStatus.planning


def test_derive_status_developing():
    defs = _default_defs()
    nodes = _nodes(
        {
            "planning": VersionNodeState.completed.value,
            "development": VersionNodeState.pending.value,
        }
    )
    assert derive_version_status(None, nodes, defs, rules=_default_rules()) == VersionStatus.developing


def test_derive_status_releasing():
    defs = _default_defs()
    nodes = _nodes(
        {
            "planning": VersionNodeState.completed.value,
            "development": VersionNodeState.completed.value,
            "release_verification": VersionNodeState.pending.value,
        }
    )
    assert derive_version_status(None, nodes, defs, rules=_default_rules()) == VersionStatus.releasing


def test_derive_status_reviewing():
    defs = _default_defs()
    nodes = _nodes(
        {
            "planning": VersionNodeState.completed.value,
            "development": VersionNodeState.completed.value,
            "release_verification": VersionNodeState.completed.value,
            "gp_review": VersionNodeState.pending.value,
        }
    )
    assert derive_version_status(None, nodes, defs, rules=_default_rules()) == VersionStatus.reviewing


def test_derive_status_ended():
    defs = _default_defs()
    nodes = _nodes({"live": VersionNodeState.completed.value})
    assert derive_version_status(None, nodes, defs, rules=_default_rules()) == VersionStatus.ended


def test_hotfix_skips_reviewing_after_release_verification():
    """热修无提审节点时，发版验证完成不应进入提审中。"""
    defs = _hotfix_defs()
    nodes = _nodes(
        {
            "planning": VersionNodeState.completed.value,
            "development": VersionNodeState.completed.value,
            "release_verification": VersionNodeState.completed.value,
            "live": VersionNodeState.pending.value,
        }
    )
    status = derive_version_status(None, nodes, defs, rules=_default_rules())
    assert status != VersionStatus.reviewing
    assert status == VersionStatus.releasing


def test_custom_rule_maps_link_verify_to_ended():
    defs = _default_defs()
    defs.append(
        VersionWorkflowNodeDef(
            project_id="proj-1",
            version_type="app_release",
            node_key="link_verify",
            label="链接验证",
            lane_index=5,
            lane_indexes=[5],
            sort_in_lane=2,
        )
    )
    nodes = _nodes(
        {
            "planning": VersionNodeState.completed.value,
            "development": VersionNodeState.completed.value,
            "release_verification": VersionNodeState.completed.value,
            "gp_review": VersionNodeState.completed.value,
            "link_verify": VersionNodeState.completed.value,
        }
    )
    custom_rules = [
        VersionStatusRuleLike(
            status="ended",
            node_keys=("link_verify",),
            sort=0,
            trigger_type="node_completed",
        ),
        *DEFAULT_VERSION_STATUS_RULES,
    ]
    assert derive_version_status(None, nodes, defs, rules=custom_rules) == VersionStatus.ended


def test_rule_skipped_when_node_not_in_defs():
    """规则引用的 node_key 不在当前版本 defs 内时跳过该条。"""
    defs = _hotfix_defs()
    nodes = _nodes(
        {
            "planning": VersionNodeState.pending.value,
            "development": VersionNodeState.pending.value,
        }
    )
    rules = [
        VersionStatusRuleLike(
            status="reviewing",
            node_keys=("gp_review",),
            sort=0,
            trigger_type="node_completed",
        ),
        VersionStatusRuleLike(
            status="planning",
            node_keys=("planning",),
            sort=10,
            trigger_type="lane",
        ),
    ]
    assert derive_version_status(None, nodes, defs, rules=rules) == VersionStatus.planning
