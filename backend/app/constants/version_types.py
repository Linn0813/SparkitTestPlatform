from __future__ import annotations

import enum


class VersionType(str, enum.Enum):
    app_release = "app_release"
    hotfix = "hotfix"


REVIEW_NODE_KEYS: frozenset[str] = frozenset(
    {
        "gp_review",
        "as_review",
        "website_link",
        "gp_approved",
        "as_approved",
    }
)

VERSION_TYPE_LABELS: dict[str, str] = {
    "app_release": "应用发版",
    "hotfix": "热修",
}

VERSION_TYPES: tuple[str, ...] = ("app_release", "hotfix")
