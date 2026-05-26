"""Tests for WeCom notification template rendering."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.requirement import Requirement
from app.services.wecom_notify import (
    DEFAULT_BUG_COMMENT_TEMPLATE,
    DEFAULT_CREATE_TEMPLATE,
    DEFAULT_REQUIREMENT_COMMENT_TEMPLATE,
    DEFAULT_STATUS_TEMPLATE,
    _collect_requirement_user_ids_for_roles,
    _is_phone_number,
    _normalize_mobile,
    _safe_template_render,
    _truncate_comment_body,
)


def test_safe_template_render_replaces_brace_placeholders():
    mapping = {
        "num": "42",
        "title": "登录失败",
        "project": "Sparkit",
        "reporter": "张三",
        "followers": "李四",
        "link": "http://localhost:5174/bugs/abc",
    }
    out = _safe_template_render(DEFAULT_CREATE_TEMPLATE, mapping)
    assert "{num}" not in out
    assert "{title}" not in out
    assert "【新建缺陷 42】登录失败" in out
    assert "项目：Sparkit" in out
    assert "提出人：张三" in out
    assert "跟进人：李四" in out
    assert "http://localhost:5174/bugs/abc" in out


def test_safe_template_render_status_template():
    mapping = {
        "num": "7",
        "title": "按钮无响应",
        "project": "Demo",
        "reporter": "王五",
        "followers": "-",
        "from_status": "待处理",
        "to_status": "进行中",
        "link": "http://example.com/bugs/7",
    }
    out = _safe_template_render(DEFAULT_STATUS_TEMPLATE, mapping)
    assert "状态：待处理 → 进行中" in out
    assert "{from_status}" not in out
    assert "{to_status}" not in out


def test_safe_template_render_keeps_unknown_placeholders():
    tpl = "【缺陷 {num}】{unknown_field}"
    out = _safe_template_render(tpl, {"num": "1"})
    assert out == "【缺陷 1】{unknown_field}"


def test_safe_template_render_does_not_use_dollar_syntax():
    tpl = "legacy $num should stay"
    out = _safe_template_render(tpl, {"num": "99"})
    assert out == "legacy $num should stay"


def test_normalize_mobile():
    assert _normalize_mobile("+86 138-0013-8000") == "8613800138000"
    assert _normalize_mobile("13800138000") == "13800138000"


def test_is_phone_number():
    assert _is_phone_number("13800138000")
    assert _is_phone_number("+86 138-0013-8000")
    assert not _is_phone_number("yuxiaoling")
    assert not _is_phone_number("123456")


def test_truncate_comment_body():
    assert _truncate_comment_body("  hello\n\nworld  ") == "hello world"
    long = "x" * 400
    out = _truncate_comment_body(long)
    assert len(out) == 300
    assert out.endswith("…")


def test_bug_comment_template_render():
    mapping = {
        "num": "3",
        "title": "闪退",
        "project": "Demo",
        "commenter": "李四",
        "comment": "复现步骤见附件",
        "link": "http://example.com/bugs/3",
    }
    out = _safe_template_render(DEFAULT_BUG_COMMENT_TEMPLATE, mapping)
    assert "【缺陷 3 新评论】闪退" in out
    assert "评论人：李四" in out
    assert "内容：复现步骤见附件" in out


def test_requirement_comment_template_render():
    mapping = {
        "num": "9",
        "title": "登录优化",
        "project": "Demo",
        "status": "开发中",
        "commenter": "王五",
        "comment": "请确认接口文档",
        "link": "http://example.com/requirements?id=9",
    }
    out = _safe_template_render(DEFAULT_REQUIREMENT_COMMENT_TEMPLATE, mapping)
    assert "【需求 9 新评论】登录优化" in out
    assert "状态：开发中" in out
    assert "评论人：王五" in out


@pytest.mark.asyncio
async def test_collect_requirement_user_ids_for_roles():
    req = MagicMock(spec=Requirement)
    req.id = "req-1"
    req.created_by = "u1"
    req.pm_id = "u2"
    req.qa_id = None
    req.tech_owner_id = None
    req.frontend_rd_id = None
    req.backend_rd_id = None
    req.designer_id = None
    req.role_assignee_ids = {"dev": ["u3", "u4"], "qa": "u5"}

    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))

    ids = await _collect_requirement_user_ids_for_roles(
        db, req, ["creator", "pm", "role_assignees"]
    )
    assert ids == ["u1", "u2", "u3", "u4", "u5"]


@pytest.mark.asyncio
async def test_collect_requirement_task_assignees():
    req = MagicMock(spec=Requirement)
    req.id = "req-2"
    req.created_by = None
    req.pm_id = None
    req.qa_id = None
    req.tech_owner_id = None
    req.frontend_rd_id = None
    req.backend_rd_id = None
    req.designer_id = None
    req.role_assignee_ids = {}

    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[("u10",), ("u10",), ("u11",)])))

    ids = await _collect_requirement_user_ids_for_roles(db, req, ["task_assignees"])
    assert ids == ["u10", "u11"]
