from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.constants.version_nodes import NODE_TO_WECOM_EVENT
from app.models.project import Project
from app.models.project_version import ProjectVersion
from app.models.template import ProjectIntegration
from app.models.user import User
from app.models.version_workflow import VersionWecomNotifyRule
from app.services.version_wecom_defaults import DEFAULT_VERSION_WECOM_TEMPLATES
from app.services.version_wecom_notify import notify_version_node_complete
from app.services.wecom_notify import _safe_template_render


def test_node_to_wecom_event_mapping():
    assert NODE_TO_WECOM_EVENT["development"] == "development_complete"
    assert NODE_TO_WECOM_EVENT["gp_review"] == "gp_review_complete"
    assert "planning" not in NODE_TO_WECOM_EVENT


def test_default_version_templates_render():
    mapping = {
        "version": "v2.0",
        "project": "Demo",
        "node": "版本开发",
        "operator": "张三",
        "link": "http://example.com/versions/abc",
    }
    for tpl in DEFAULT_VERSION_WECOM_TEMPLATES.values():
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
        event_key="development_complete",
        message_template=DEFAULT_VERSION_WECOM_TEMPLATES["development_complete"],
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
        "app.services.version_wecom_notify._send_version_wecom",
        new=AsyncMock(return_value=1),
    ) as send_mock:
        count = await notify_version_node_complete(db, version, "development", "op-1")
        assert count == 1
        send_mock.assert_awaited_once()
        assert send_mock.call_args.kwargs["target_ids"] == ["user-2"]


@pytest.mark.asyncio
async def test_notify_skips_when_no_event():
    version = ProjectVersion(
        id="ver-1",
        project_id="proj-1",
        num=1,
        name="v1.0",
        created_by="u1",
    )
    db = AsyncMock()
    count = await notify_version_node_complete(db, version, "planning", "op-1")
    assert count is None
