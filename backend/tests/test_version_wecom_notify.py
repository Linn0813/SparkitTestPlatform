from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.project import Project
from app.models.project_version import ProjectVersion
from app.models.template import ProjectIntegration
from app.models.user import User
from app.models.version_workflow import VersionWecomNotifyRule
from app.services.version_wecom_defaults import default_template_for_node
from app.services.version_wecom_notify import notify_version_node_complete
from app.services.wecom_notify import _safe_template_render


def test_default_version_templates_render():
    mapping = {
        "version": "v2.0",
        "project": "Demo",
        "node": "版本开发",
        "operator": "张三",
        "link": "http://example.com/versions/abc",
    }
    tpl = default_template_for_node("development", "版本开发")
    out = _safe_template_render(tpl, mapping)
    assert "{version}" not in out
    assert "v2.0" in out
    assert "Demo" in out


@pytest.mark.asyncio
async def test_notify_version_node_complete_invokes_send():
    version = ProjectVersion(
        id="ver-1",
        project_id="proj-1",
        num=1,
        name="v2.0",
        created_by="u1",
    )
    rule = VersionWecomNotifyRule(
        id="rule-1",
        project_id="proj-1",
        node_key="development",
        message_template=default_template_for_node("development", "版本开发"),
        notify_user_ids=["user-2"],
        enabled=True,
    )

    db = AsyncMock()
    db.get = AsyncMock(
        side_effect=lambda model, pk: {
            (Project, "proj-1"): Project(id="proj-1", name="Demo", is_enabled=True),
            (User, "op-1"): User(id="op-1", name="张三", email="a@b.com", password_hash="x"),
        }.get((model, pk))
    )

    integ = ProjectIntegration(
        project_id="proj-1",
        version_wecom_enabled=True,
        version_wecom_webhook_url="https://example.com/hook",
        app_public_url="http://example.com",
    )

    rule_result = MagicMock()
    rule_result.scalar_one_or_none.return_value = rule
    integ_result = MagicMock()
    integ_result.scalar_one_or_none.return_value = integ
    db.execute = AsyncMock(side_effect=[rule_result, integ_result])

    with patch(
        "app.services.version_wecom_notify.is_version_wecom_configured",
        new=AsyncMock(return_value=True),
    ), patch(
        "app.services.version_wecom_notify.load_project_notifyable_nodes",
        new=AsyncMock(return_value={"development": "版本开发"}),
    ), patch(
        "app.services.version_wecom_notify._send_version_wecom",
        new=AsyncMock(return_value=1),
    ) as send_mock:
        count = await notify_version_node_complete(db, version, "development", "op-1")
        assert count == 1
        send_mock.assert_awaited_once()
        assert send_mock.call_args.kwargs["target_ids"] == ["user-2"]


@pytest.mark.asyncio
async def test_notify_planning_when_rule_configured():
    version = ProjectVersion(
        id="ver-1",
        project_id="proj-1",
        num=1,
        name="v1.0",
        created_by="u1",
    )
    rule = VersionWecomNotifyRule(
        id="rule-1",
        project_id="proj-1",
        node_key="planning",
        message_template=default_template_for_node("planning", "版本规划"),
        notify_user_ids=[],
        enabled=True,
    )

    db = AsyncMock()
    db.get = AsyncMock(
        side_effect=lambda model, pk: {
            (Project, "proj-1"): Project(id="proj-1", name="Demo", is_enabled=True),
            (User, "op-1"): User(id="op-1", name="张三", email="a@b.com", password_hash="x"),
        }.get((model, pk))
    )
    integ = ProjectIntegration(
        project_id="proj-1",
        version_wecom_enabled=True,
        version_wecom_webhook_url="https://example.com/hook",
    )
    rule_result = MagicMock()
    rule_result.scalar_one_or_none.return_value = rule
    integ_result = MagicMock()
    integ_result.scalar_one_or_none.return_value = integ
    db.execute = AsyncMock(side_effect=[rule_result, integ_result])

    with patch(
        "app.services.version_wecom_notify.is_version_wecom_configured",
        new=AsyncMock(return_value=True),
    ), patch(
        "app.services.version_wecom_notify.load_project_notifyable_nodes",
        new=AsyncMock(return_value={"planning": "版本规划"}),
    ), patch(
        "app.services.version_wecom_notify._send_version_wecom",
        new=AsyncMock(return_value=0),
    ) as send_mock:
        count = await notify_version_node_complete(db, version, "planning", "op-1")
        assert count == 0
        send_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_notify_skips_when_no_rule():
    version = ProjectVersion(
        id="ver-1",
        project_id="proj-1",
        num=1,
        name="v1.0",
        created_by="u1",
    )
    db = AsyncMock()
    rule_result = MagicMock()
    rule_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=rule_result)

    count = await notify_version_node_complete(db, version, "development", "op-1")
    assert count is None
