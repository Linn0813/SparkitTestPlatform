from __future__ import annotations

import pytest

from app.constants.version_status_rules import (
    DEFAULT_APP_RELEASE_STATUS_RULES,
    DEFAULT_HOTFIX_STATUS_RULES,
    DEFAULT_VERSION_STATUS_RULES,
    default_status_rules_for_type,
)
from app.models.template import VersionWorkflowNodeDef
from app.services.version_status_rules import (
    _default_payload_for_type,
    default_version_status_rule_likes,
    validate_version_status_rules_payload,
)
from app.services.version_workflow_defaults import (
    DEFAULT_APP_RELEASE_WORKFLOW_NODES,
    DEFAULT_HOTFIX_WORKFLOW_NODES,
)


def _workflow_defs() -> list[VersionWorkflowNodeDef]:
    return [
        VersionWorkflowNodeDef(
            project_id="proj-1",
            version_type="app_release",
            **item,
        )
        for item in DEFAULT_APP_RELEASE_WORKFLOW_NODES
    ]


def _hotfix_workflow_defs() -> list[VersionWorkflowNodeDef]:
    return [
        VersionWorkflowNodeDef(
            project_id="proj-1",
            version_type="hotfix",
            **item,
        )
        for item in DEFAULT_HOTFIX_WORKFLOW_NODES
    ]


def test_default_rules_differ_by_version_type():
    app_rules = default_version_status_rule_likes("app_release")
    hotfix_rules = default_version_status_rule_likes("hotfix")
    assert any(r.status == "reviewing" for r in app_rules)
    assert not any(r.status == "reviewing" for r in hotfix_rules)
    assert len(hotfix_rules) == len(DEFAULT_HOTFIX_STATUS_RULES)
    assert len(app_rules) == len(DEFAULT_APP_RELEASE_STATUS_RULES)


def test_validate_accepts_hotfix_default_payload():
    payload = [
        {
            "status": r.status,
            "node_keys": list(r.node_keys),
            "sort": r.sort,
            "trigger_type": r.trigger_type,
        }
        for r in default_status_rules_for_type("hotfix")
    ]
    result = validate_version_status_rules_payload(payload, workflow_defs=_hotfix_workflow_defs())
    assert len(result) == len(DEFAULT_HOTFIX_STATUS_RULES)


def test_default_payload_skips_unknown_nodes():
    defs = _workflow_defs()
    defs = [d for d in defs if d.node_key != "live"]
    payload = _default_payload_for_type("app_release", defs)
    assert payload
    assert all("live" not in rule["node_keys"] for rule in payload)
    validate_version_status_rules_payload(payload, workflow_defs=defs)


def test_validate_accepts_default_payload():
    payload = [
        {
            "status": r.status,
            "node_keys": list(r.node_keys),
            "sort": r.sort,
            "trigger_type": r.trigger_type,
        }
        for r in DEFAULT_VERSION_STATUS_RULES
    ]
    result = validate_version_status_rules_payload(payload, workflow_defs=_workflow_defs())
    assert len(result) == len(DEFAULT_VERSION_STATUS_RULES)


def test_validate_rejects_empty_rules():
    with pytest.raises(ValueError, match="至少配置一条"):
        validate_version_status_rules_payload([], workflow_defs=_workflow_defs())


def test_validate_rejects_unknown_status():
    with pytest.raises(ValueError, match="状态无效"):
        validate_version_status_rules_payload(
            [{"status": "invalid", "node_keys": ["planning"], "sort": 0, "trigger_type": "lane"}],
            workflow_defs=_workflow_defs(),
        )


def test_validate_rejects_unknown_node_key():
    with pytest.raises(ValueError, match="未知节点"):
        validate_version_status_rules_payload(
            [{"status": "planning", "node_keys": ["not_a_node"], "sort": 0, "trigger_type": "lane"}],
            workflow_defs=_workflow_defs(),
        )


def test_validate_allows_status_hold_without_nodes():
    result = validate_version_status_rules_payload(
        [{"status": "planning", "node_keys": [], "sort": 0, "trigger_type": "status_hold"}],
        workflow_defs=_workflow_defs(),
    )
    assert result[0]["node_keys"] == []
