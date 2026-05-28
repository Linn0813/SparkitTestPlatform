from __future__ import annotations

from app.constants.version_nodes import VERSION_WECOM_EVENT_KEYS

DEFAULT_VERSION_WECOM_TEMPLATES: dict[str, str] = {
    "development_complete": (
        "【版本开发完成】{version}\n"
        "项目：{project}\n"
        "操作人：{operator}\n"
        "{link}"
    ),
    "release_verification_complete": (
        "【发版验证完成】{version}\n"
        "项目：{project}\n"
        "操作人：{operator}\n"
        "{link}"
    ),
    "gp_review_complete": (
        "【GP提审完成】{version}\n"
        "项目：{project}\n"
        "操作人：{operator}\n"
        "{link}"
    ),
    "as_review_complete": (
        "【AS提审完成】{version}\n"
        "项目：{project}\n"
        "操作人：{operator}\n"
        "{link}"
    ),
    "website_link_complete": (
        "【官网链接完成】{version}\n"
        "项目：{project}\n"
        "操作人：{operator}\n"
        "{link}"
    ),
    "gp_approved_complete": (
        "【GP过审完成】{version}\n"
        "项目：{project}\n"
        "操作人：{operator}\n"
        "{link}"
    ),
    "as_approved_complete": (
        "【AS过审完成】{version}\n"
        "项目：{project}\n"
        "操作人：{operator}\n"
        "{link}"
    ),
}

WECOM_EVENT_LABELS: dict[str, str] = {
    "development_complete": "版本开发完成",
    "release_verification_complete": "发版验证完成",
    "gp_review_complete": "GP提审完成",
    "as_review_complete": "AS提审完成",
    "website_link_complete": "官网链接完成",
    "gp_approved_complete": "GP过审完成",
    "as_approved_complete": "AS过审完成",
}


def default_template_for_node(node_key: str, label: str) -> str:
    legacy_key = f"{node_key}_complete"
    if legacy_key in DEFAULT_VERSION_WECOM_TEMPLATES:
        return DEFAULT_VERSION_WECOM_TEMPLATES[legacy_key]
    return (
        f"【{label}完成】{{version}}\n"
        "项目：{project}\n"
        "操作人：{operator}\n"
        "{link}"
    )


def all_default_templates() -> list[tuple[str, str]]:
    return [(key, DEFAULT_VERSION_WECOM_TEMPLATES[key]) for key in VERSION_WECOM_EVENT_KEYS]
