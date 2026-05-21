from __future__ import annotations

REQUIREMENT_STATUS_KEYS: tuple[str, ...] = ("not_tested", "testing", "accepted")

REQUIREMENT_STATUS_LABELS: dict[str, str] = {
    "not_tested": "未转测",
    "testing": "测试中",
    "accepted": "已验收",
}


def requirement_status_label(key: str) -> str:
    return REQUIREMENT_STATUS_LABELS.get(key, key)
