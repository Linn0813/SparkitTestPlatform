"""Tests for public URL resolution."""

from app.core.public_url import (
    build_bug_detail_url,
    build_requirement_detail_url,
    resolve_public_base_url,
)


def test_resolve_prefers_project_url(monkeypatch):
    monkeypatch.setattr(
        "app.core.public_url.settings.app_public_url",
        "http://localhost:5174",
    )
    monkeypatch.setattr(
        "app.core.public_url.settings.cors_origins",
        "",
    )
    assert resolve_public_base_url("http://192.168.1.10:5174") == "http://192.168.1.10:5174"


def test_resolve_falls_back_to_cors_when_env_is_localhost(monkeypatch):
    monkeypatch.setattr(
        "app.core.public_url.settings.app_public_url",
        "http://localhost:5174",
    )
    monkeypatch.setattr(
        "app.core.public_url.settings.cors_origins",
        "http://localhost:5174,http://10.0.0.5:5174",
    )
    assert resolve_public_base_url(None) == "http://10.0.0.5:5174"


def test_build_bug_detail_url():
    url = build_bug_detail_url("bug-123", project_url="http://example.com:5174")
    assert url == "http://example.com:5174/bugs/bug-123"


def test_build_requirement_detail_url():
    url = build_requirement_detail_url("req-456", project_url="http://example.com:5174")
    assert url == "http://example.com:5174/requirements?id=req-456"
