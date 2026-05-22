"""Tests for WeCom notification template rendering."""

from app.services.wecom_notify import (
    DEFAULT_CREATE_TEMPLATE,
    DEFAULT_STATUS_TEMPLATE,
    _is_phone_number,
    _normalize_mobile,
    _safe_template_render,
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
