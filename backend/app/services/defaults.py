from __future__ import annotations

DEFAULT_CASE_FIELDS: list = []

DEFAULT_BUG_FIELDS: list = []

DEFAULT_NOTIFY_ROLES = ["reporter", "followers"]

DEFAULT_BUG_STATUSES = [
    {
        "key": "pending_confirm",
        "label": "待确认",
        "sort": 0,
        "is_terminal": False,
        "notify_wecom": False,
        "notify_roles": DEFAULT_NOTIFY_ROLES,
    },
    {
        "key": "in_progress",
        "label": "处理中",
        "sort": 1,
        "is_terminal": False,
        "notify_wecom": False,
        "notify_roles": DEFAULT_NOTIFY_ROLES,
    },
    {
        "key": "fixed",
        "label": "已修复",
        "sort": 2,
        "is_terminal": False,
        "notify_wecom": True,
        "notify_roles": DEFAULT_NOTIFY_ROLES,
    },
    {
        "key": "accepted",
        "label": "已验收",
        "sort": 3,
        "is_terminal": True,
        "notify_wecom": False,
        "notify_roles": DEFAULT_NOTIFY_ROLES,
    },
    {
        "key": "rejected",
        "label": "已拒绝",
        "sort": 4,
        "is_terminal": True,
        "notify_wecom": False,
        "notify_roles": DEFAULT_NOTIFY_ROLES,
    },
    {
        "key": "suspended",
        "label": "挂起",
        "sort": 5,
        "is_terminal": False,
        "notify_wecom": False,
        "notify_roles": DEFAULT_NOTIFY_ROLES,
    },
    {
        "key": "to_requirement",
        "label": "转需求",
        "sort": 6,
        "is_terminal": False,
        "notify_wecom": False,
        "notify_roles": DEFAULT_NOTIFY_ROLES,
    },
]
