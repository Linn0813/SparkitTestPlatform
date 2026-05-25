from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

StatusRuleTrigger = Literal["status_hold", "node_completed", "lane"]

STATUS_RULE_TRIGGERS: tuple[StatusRuleTrigger, ...] = ("status_hold", "node_completed", "lane")


@dataclass(frozen=True)
class StatusRuleLike:
    status: str
    node_keys: tuple[str, ...]
    sort: int
    trigger_type: StatusRuleTrigger = "lane"


def lane_match_requirements(
    status: str, node_keys: tuple[str, ...]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """根据状态与关联节点推断阶段匹配条件（无需单独配置）。"""
    keys = set(node_keys)
    if status == "draft" and "prd_output" in keys:
        return (), ("prd_output",)
    if status == "designing" and "req_design" in keys:
        return ("prd_output",), ("req_design",)
    if status == "pending_release" and "released" in keys:
        return (), ("released",)
    return (), node_keys


# sort 越小越优先
DEFAULT_REQUIREMENT_STATUS_RULES: tuple[StatusRuleLike, ...] = (
    StatusRuleLike(status="closed", node_keys=(), sort=0, trigger_type="status_hold"),
    StatusRuleLike(
        status="released",
        node_keys=("released",),
        sort=1,
        trigger_type="node_completed",
    ),
    StatusRuleLike(
        status="testing",
        node_keys=("req_test", "product_experience", "ui_restoration"),
        sort=10,
        trigger_type="lane",
    ),
    StatusRuleLike(
        status="developing",
        node_keys=("frontend_dev", "backend_dev", "integration"),
        sort=11,
        trigger_type="lane",
    ),
    StatusRuleLike(status="pending_review", node_keys=("req_review",), sort=12, trigger_type="lane"),
    StatusRuleLike(status="draft", node_keys=("prd_output",), sort=13, trigger_type="lane"),
    StatusRuleLike(status="designing", node_keys=("req_design",), sort=14, trigger_type="lane"),
    StatusRuleLike(status="pending_release", node_keys=("released",), sort=15, trigger_type="lane"),
)
