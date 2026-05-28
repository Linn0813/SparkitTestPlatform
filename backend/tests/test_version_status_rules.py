from __future__ import annotations

import pytest

from app.constants.version_status_rules import DEFAULT_VERSION_STATUS_RULES
from app.models.template import VersionWorkflowNodeDef
from app.services.version_status_rules import validate_version_status_rules_payload
from app.services.version_workflow_defaults import DEFAULT_APP_RELEASE_WORKFLOW_NODES


def _workflow_defs() -> list[VersionWorkflowNodeDef]:
    return [
        VersionWorkflowNodeDef(
            project_id="proj-1",
            version_type="app_release",
            **item,
        )
        for item in DEFAULT_APP_RELEASE_WORKFLOW_NODES
    ]


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
