from __future__ import annotations

REQUIREMENT_STATUS_KEYS: tuple[str, ...] = (
    "draft",
    "pending_review",
    "designing",
    "developing",
    "testing",
    "pending_release",
    "released",
    "completed",
    "closed",
)

REQUIREMENT_STATUS_LABELS: dict[str, str] = {
    "draft": "草稿",
    "pending_review": "待评审",
    "designing": "设计中",
    "developing": "开发中",
    "testing": "测试中",
    "pending_release": "待发版",
    "released": "已发版",
    "completed": "已完成",
    "closed": "已关闭",
}

# 手动保持的状态：不参与工作流推导
HOLD_REQUIREMENT_STATUS_KEYS: frozenset[str] = frozenset({"closed", "completed"})

# 终结态：不参与进行中待办推导
TERMINAL_REQUIREMENT_STATUS_KEYS: frozenset[str] = frozenset({"released", "completed", "closed"})

# 工作台待办：开发中
TESTER_TODO_DEVELOPING_STATUS_KEYS: tuple[str, ...] = ("developing",)

# 工作台待办：测试中 + 待发版
TESTER_TODO_TESTING_STATUS_KEYS: tuple[str, ...] = ("testing", "pending_release")


def requirement_status_label(key: str) -> str:
    return REQUIREMENT_STATUS_LABELS.get(key, key)
