from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.template import VersionWorkflowNodeDef
from app.models.version_workflow import VersionWecomNotifyRule
from app.services.version_wecom_defaults import default_template_for_node
from app.services.version_wecom_rules import (
    VersionWecomRuleError,
    list_version_wecom_rule_options,
    load_project_notifyable_nodes,
    validate_rule_node_key,
)


def test_default_template_for_node_builtin():
    tpl = default_template_for_node("development", "版本开发")
    assert "版本开发完成" in tpl
    assert "{version}" in tpl


def test_default_template_for_node_custom():
    tpl = default_template_for_node("custom_step", "自定义步骤")
    assert "自定义步骤完成" in tpl
    assert "{version}" in tpl


@pytest.mark.asyncio
async def test_load_project_notifyable_nodes_dedupes():
    db = AsyncMock()

    async def fake_load(db_arg, project_id, version_type):
        if version_type == "app_release":
            return [
                VersionWorkflowNodeDef(
                    project_id=project_id,
                    version_type=version_type,
                    node_key="development",
                    label="版本开发",
                    lane_index=1,
                ),
                VersionWorkflowNodeDef(
                    project_id=project_id,
                    version_type=version_type,
                    node_key="gp_review",
                    label="GP提审",
                    lane_index=3,
                ),
            ]
        return [
            VersionWorkflowNodeDef(
                project_id=project_id,
                version_type=version_type,
                node_key="development",
                label="版本开发",
                lane_index=1,
            ),
            VersionWorkflowNodeDef(
                project_id=project_id,
                version_type=version_type,
                node_key="live",
                label="已上线",
                lane_index=3,
            ),
        ]

    with patch(
        "app.services.version_wecom_rules.load_project_version_workflow_defs",
        new=fake_load,
    ):
        nodes = await load_project_notifyable_nodes(db, "proj-1")

    assert nodes == {
        "development": "版本开发",
        "gp_review": "GP提审",
        "live": "已上线",
    }


@pytest.mark.asyncio
async def test_validate_rule_node_key_rejects_unknown():
    db = AsyncMock()
    with patch(
        "app.services.version_wecom_rules.load_project_notifyable_nodes",
        new=AsyncMock(return_value={"development": "版本开发"}),
    ):
        with pytest.raises(VersionWecomRuleError, match="未知工作流节点"):
            await validate_rule_node_key(db, "proj-1", "unknown")


@pytest.mark.asyncio
async def test_list_rule_options_from_workflow():
    project_id = "proj-opts"
    db_nodes = [
        VersionWecomNotifyRule(
            project_id=project_id,
            node_key="development",
            message_template="tpl",
            enabled=True,
        )
    ]

    class FakeSession:
        async def execute(self, stmt):
            class Result:
                def all(self_inner):
                    return [(n.node_key,) for n in db_nodes if n.project_id == project_id]

            return Result()

    with patch(
        "app.services.version_wecom_rules.load_project_notifyable_nodes",
        new=AsyncMock(
            return_value={
                "development": "版本开发",
                "gp_review": "GP提审",
                "planning": "版本规划",
            }
        ),
    ):
        options = await list_version_wecom_rule_options(project_id, FakeSession())

    dev = next(o for o in options if o["node_key"] == "development")
    gp = next(o for o in options if o["node_key"] == "gp_review")
    planning = next(o for o in options if o["node_key"] == "planning")

    assert dev["configured"] is True
    assert gp["configured"] is False
    assert planning["configured"] is False
    assert dev["node_label"] == "版本开发"
