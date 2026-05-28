from __future__ import annotations

VERSION_NODE_KEYS: tuple[str, ...] = (
    "planning",
    "development",
    "release_verification",
    "gp_review",
    "as_review",
    "website_link",
    "live",
)

VERSION_NODE_LABELS: dict[str, str] = {
    "planning": "版本规划",
    "development": "版本开发",
    "release_verification": "发版验证",
    "gp_review": "GP提审",
    "as_review": "AS提审",
    "website_link": "官网链接",
    "live": "已上线",
}

SERIAL_NODE_KEYS: tuple[str, ...] = (
    "planning",
    "development",
    "release_verification",
    "live",
)

REVIEW_NODE_KEYS: tuple[str, ...] = ("gp_review", "as_review", "website_link")

# node_key -> prerequisite node keys that must be completed
VERSION_NODE_PREREQUISITES: dict[str, tuple[str, ...]] = {
    "planning": (),
    "development": ("planning",),
    "release_verification": ("development",),
    "gp_review": ("release_verification",),
    "as_review": ("release_verification",),
    "website_link": ("release_verification",),
    "live": ("gp_review", "as_review", "website_link"),
}

# Nodes that must be reopened when reopening a given node (parallel review siblings stay intact)
VERSION_NODE_DEPENDENTS: dict[str, tuple[str, ...]] = {
    "planning": VERSION_NODE_KEYS,
    "development": (
        "development",
        "release_verification",
        "gp_review",
        "as_review",
        "website_link",
        "live",
    ),
    "release_verification": (
        "release_verification",
        "gp_review",
        "as_review",
        "website_link",
        "live",
    ),
    "gp_review": ("gp_review", "live"),
    "as_review": ("as_review", "live"),
    "website_link": ("website_link", "live"),
    "live": ("live",),
}

VERSION_WECOM_EVENT_KEYS: tuple[str, ...] = (
    "development_complete",
    "release_verification_complete",
    "gp_review_complete",
    "as_review_complete",
    "website_link_complete",
)

NODE_TO_WECOM_EVENT: dict[str, str] = {
    "development": "development_complete",
    "release_verification": "release_verification_complete",
    "gp_review": "gp_review_complete",
    "as_review": "as_review_complete",
    "website_link": "website_link_complete",
}

VERSION_STATUS_LABELS: dict[str, str] = {
    "planning": "规划中",
    "developing": "开发中",
    "releasing": "发版中",
    "reviewing": "提审中",
    "ended": "已结束",
}
