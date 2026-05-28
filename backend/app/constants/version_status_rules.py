from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

VersionStatusRuleTrigger = Literal["status_hold", "node_completed", "lane"]

VERSION_STATUS_RULE_TRIGGERS: tuple[VersionStatusRuleTrigger, ...] = (
    "status_hold",
    "node_completed",
    "lane",
)

VERSION_STATUS_KEYS: tuple[str, ...] = (
    "planning",
    "developing",
    "releasing",
    "reviewing",
    "ended",
)


@dataclass(frozen=True)
class VersionStatusRuleLike:
    status: str
    node_keys: tuple[str, ...]
    sort: int
    trigger_type: VersionStatusRuleTrigger = "lane"


def version_lane_match_requirements(
    status: str, node_keys: tuple[str, ...]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """版本 lane 规则：关联节点至少一个未完成即命中。"""
    return (), node_keys


# sort 越小越优先
DEFAULT_VERSION_STATUS_RULES: tuple[VersionStatusRuleLike, ...] = (
    VersionStatusRuleLike(
        status="ended",
        node_keys=("live",),
        sort=0,
        trigger_type="node_completed",
    ),
    VersionStatusRuleLike(
        status="reviewing",
        node_keys=("release_verification",),
        sort=1,
        trigger_type="node_completed",
    ),
    VersionStatusRuleLike(
        status="releasing",
        node_keys=("development",),
        sort=2,
        trigger_type="node_completed",
    ),
    VersionStatusRuleLike(
        status="developing",
        node_keys=("planning",),
        sort=3,
        trigger_type="node_completed",
    ),
    VersionStatusRuleLike(
        status="planning",
        node_keys=("planning",),
        sort=10,
        trigger_type="lane",
    ),
)
