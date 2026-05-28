from __future__ import annotations

from app.constants.version_types import VersionType

DEFAULT_APP_RELEASE_WORKFLOW_NODES: list[dict] = [
    {"node_key": "planning", "label": "版本规划", "lane_index": 0, "lane_indexes": [0], "sort_in_lane": 0},
    {"node_key": "development", "label": "版本开发", "lane_index": 1, "lane_indexes": [1], "sort_in_lane": 0},
    {
        "node_key": "release_verification",
        "label": "发版验证",
        "lane_index": 2,
        "lane_indexes": [2],
        "sort_in_lane": 0,
    },
    {"node_key": "gp_review", "label": "GP提审", "lane_index": 3, "lane_indexes": [3], "sort_in_lane": 0},
    {"node_key": "as_review", "label": "AS提审", "lane_index": 3, "lane_indexes": [3], "sort_in_lane": 1},
    {"node_key": "website_link", "label": "官网链接", "lane_index": 3, "lane_indexes": [3, 4], "sort_in_lane": 2},
    {"node_key": "gp_approved", "label": "GP过审", "lane_index": 4, "lane_indexes": [4], "sort_in_lane": 0},
    {"node_key": "as_approved", "label": "AS过审", "lane_index": 4, "lane_indexes": [4], "sort_in_lane": 1},
    {"node_key": "live", "label": "已上线", "lane_index": 5, "lane_indexes": [5], "sort_in_lane": 0},
]

DEFAULT_HOTFIX_WORKFLOW_NODES: list[dict] = [
    {"node_key": "planning", "label": "版本规划", "lane_index": 0, "lane_indexes": [0], "sort_in_lane": 0},
    {"node_key": "development", "label": "版本开发", "lane_index": 1, "lane_indexes": [1], "sort_in_lane": 0},
    {
        "node_key": "release_verification",
        "label": "发版验证",
        "lane_index": 2,
        "lane_indexes": [2],
        "sort_in_lane": 0,
    },
    {"node_key": "live", "label": "已上线", "lane_index": 3, "lane_indexes": [3], "sort_in_lane": 0},
]

DEFAULT_VERSION_WORKFLOW_BY_TYPE: dict[str, list[dict]] = {
    VersionType.app_release.value: DEFAULT_APP_RELEASE_WORKFLOW_NODES,
    VersionType.hotfix.value: DEFAULT_HOTFIX_WORKFLOW_NODES,
}

APP_RELEASE_NODE_KEYS: frozenset[str] = frozenset(n["node_key"] for n in DEFAULT_APP_RELEASE_WORKFLOW_NODES)
