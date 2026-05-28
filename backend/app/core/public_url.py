from __future__ import annotations

from app.core.config import settings


def _is_localhost(url: str) -> bool:
    lower = url.lower()
    return "localhost" in lower or "127.0.0.1" in lower


def resolve_public_base_url(project_url: str | None = None) -> str:
    """企微/外链用的前端根地址：项目配置 > 环境变量 > CORS 中非 localhost 源。"""
    for candidate in (project_url, settings.app_public_url):
        if candidate and str(candidate).strip():
            base = str(candidate).strip().rstrip("/")
            if not _is_localhost(base):
                return base

    for origin in settings.cors_origin_list:
        base = origin.strip().rstrip("/")
        if base and not _is_localhost(base):
            return base

    return (settings.app_public_url or "http://localhost:5174").strip().rstrip("/")


def build_bug_detail_url(bug_id: str, *, project_url: str | None = None) -> str:
    return f"{resolve_public_base_url(project_url)}/bugs/{bug_id}"


def build_requirement_detail_url(requirement_id: str, *, project_url: str | None = None) -> str:
    return f"{resolve_public_base_url(project_url)}/requirements?id={requirement_id}"


def build_version_detail_url(version_id: str, *, project_url: str | None = None) -> str:
    return f"{resolve_public_base_url(project_url)}/versions/{version_id}"
