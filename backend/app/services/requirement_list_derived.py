"""Derived fields for requirement list (developers, dev handoff date)."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from app.constants.requirement_nodes import DEVELOPER_ROLE_KEYS, DEVELOPMENT_NODE_KEYS
from app.models.requirement import Requirement
from app.schemas.user import UserOut

if TYPE_CHECKING:
    from app.schemas.requirement import RequirementNodeProgressOut


def compute_dev_handoff_date(nodes: list[RequirementNodeProgressOut]) -> date | None:
    ends: list[date] = []
    for node in nodes:
        if node.node_key not in DEVELOPMENT_NODE_KEYS or not node.enabled:
            continue
        if node.planned_schedule_end is not None:
            ends.append(node.planned_schedule_end)
    return max(ends) if ends else None


def collect_developer_user_ids(row: Requirement) -> list[str]:
    from app.services.requirement_serializers import normalize_role_assignee_ids

    assignees = normalize_role_assignee_ids(row)
    seen: set[str] = set()
    out: list[str] = []
    for role_key in DEVELOPER_ROLE_KEYS:
        for uid in assignees.get(role_key) or []:
            if uid and uid not in seen:
                seen.add(uid)
                out.append(uid)
    return out


def build_developers_out(user_ids: list[str], users_map: dict[str, UserOut]) -> list[UserOut]:
    return [users_map[uid] for uid in user_ids if uid in users_map]
