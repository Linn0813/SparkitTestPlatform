from __future__ import annotations

from app.constants.requirement_nodes import REQUIREMENT_NODE_LABELS, REQUIREMENT_NODE_PHASES, REQUIREMENT_NODE_ROLE_KEYS

DEFAULT_REQUIREMENT_WORKFLOW_NODES: list[dict] = []
_lane = 0
for phase in REQUIREMENT_NODE_PHASES:
    for sort_in_lane, node_key in enumerate(phase):
        DEFAULT_REQUIREMENT_WORKFLOW_NODES.append(
            {
                "node_key": node_key,
                "label": REQUIREMENT_NODE_LABELS[node_key],
                "role_keys": REQUIREMENT_NODE_ROLE_KEYS[node_key],
                "lane_index": _lane,
                "lane_indexes": [_lane],
                "blocks_lane_gate": True,
                "sort_in_lane": sort_in_lane,
            }
        )
    _lane += 1

# 技术优化类需求默认不启用的节点 key
TECH_OPTIMIZATION_DEFAULT_DISABLED_NODES: frozenset[str] = frozenset(
    {"product_experience", "ui_restoration", "req_design"}
)
