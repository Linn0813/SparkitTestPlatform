from __future__ import annotations

REQUIREMENT_NODE_KEYS: tuple[str, ...] = (
    "prd_output",
    "req_design",
    "req_review",
    "frontend_dev",
    "backend_dev",
    "integration",
    "req_test",
    "product_experience",
    "ui_restoration",
    "released",
)

REQUIREMENT_NODE_LABELS: dict[str, str] = {
    "prd_output": "PRD输出",
    "req_design": "需求设计",
    "req_review": "需求评审",
    "frontend_dev": "前端开发",
    "backend_dev": "后端开发",
    "integration": "联调",
    "req_test": "需求测试",
    "product_experience": "产品体验",
    "ui_restoration": "UI还原",
    "released": "已发版",
}

# 并行阶段分组
REQUIREMENT_NODE_PHASES: tuple[tuple[str, ...], ...] = (
    ("prd_output", "req_design"),
    ("req_review",),
    ("frontend_dev", "backend_dev"),
    ("integration",),
    ("req_test", "product_experience", "ui_restoration"),
    ("released",),
)

# 节点默认负责角色（UI 提示；推进权限为 catalog 成员）
REQUIREMENT_NODE_ROLE_KEYS: dict[str, list[str]] = {
    "prd_output": ["pm"],
    "req_design": ["pm"],
    "req_review": ["tech_owner"],
    "frontend_dev": ["frontend_rd"],
    "backend_dev": ["backend_rd"],
    "integration": ["frontend_rd", "backend_rd"],
    "req_test": ["qa"],
    "product_experience": ["pm"],
    "ui_restoration": ["designer"],
    "released": ["pm"],
}

# 技术优化类需求可跳过的节点
TECH_OPTIMIZATION_SKIPPABLE_NODES: frozenset[str] = frozenset(
    {"product_experience", "ui_restoration", "req_design"}
)

DEVELOPMENT_NODE_KEYS: tuple[str, ...] = ("frontend_dev", "backend_dev", "integration")

DEVELOPER_ROLE_KEYS: tuple[str, ...] = ("frontend_rd", "backend_rd", "tech_owner")

REQUIREMENT_ROLE_KEYS: tuple[str, ...] = (
    "frontend_rd",
    "backend_rd",
    "pm",
    "tech_owner",
    "qa",
    "designer",
)

REQUIREMENT_ROLE_LABELS: dict[str, str] = {
    "frontend_rd": "前端RD",
    "backend_rd": "后端RD",
    "pm": "PM",
    "tech_owner": "技术Owner",
    "qa": "测试QA",
    "designer": "设计",
}


def requirement_node_label(key: str) -> str:
    return REQUIREMENT_NODE_LABELS.get(key, key)


def requirement_role_label(key: str) -> str:
    return REQUIREMENT_ROLE_LABELS.get(key, key)


def requirement_role_labels(keys: list[str]) -> str:
    return "、".join(requirement_role_label(k) for k in keys)
