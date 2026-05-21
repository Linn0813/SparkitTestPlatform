from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Select, not_, select

from app.models.bug import Bug, BugFollowerLink
from app.models.requirement import BugPlanLink, BugRequirementLink
from app.services.custom_field_filters import (
    FILTER_EMPTY,
    apply_custom_field_filters,
    parse_custom_filters,
)

__all__ = ["FILTER_EMPTY", "parse_custom_filters", "apply_bug_list_filters"]


def apply_bug_list_filters(
    stmt: Select,
    *,
    status_key: Optional[str] = None,
    assignee_id: Optional[str] = None,
    reporter_id: Optional[str] = None,
    follower_id: Optional[str] = None,
    plan_version_id: Optional[str] = None,
    found_version_id: Optional[str] = None,
    requirement_id: Optional[str] = None,
    plan_id: Optional[str] = None,
    q: Optional[str] = None,
    template_fields: list[dict[str, Any]],
    custom_filters: Optional[dict[str, str]] = None,
) -> Select:
    if status_key:
        stmt = stmt.where(Bug.status_key == status_key)
    if assignee_id:
        if assignee_id == FILTER_EMPTY:
            stmt = stmt.where(Bug.assignee_id.is_(None))
        else:
            stmt = stmt.where(Bug.assignee_id == assignee_id)
    if reporter_id:
        stmt = stmt.where(Bug.reporter_id == reporter_id)
    if follower_id:
        if follower_id == FILTER_EMPTY:
            stmt = stmt.where(
                not_(Bug.id.in_(select(BugFollowerLink.bug_id).distinct()))
            )
        else:
            stmt = stmt.where(
                Bug.id.in_(
                    select(BugFollowerLink.bug_id).where(BugFollowerLink.user_id == follower_id)
                )
            )
    if plan_version_id:
        if plan_version_id == FILTER_EMPTY:
            stmt = stmt.where(Bug.plan_version_id.is_(None))
        else:
            stmt = stmt.where(Bug.plan_version_id == plan_version_id)
    if found_version_id:
        if found_version_id == FILTER_EMPTY:
            stmt = stmt.where(Bug.found_version_id.is_(None))
        else:
            stmt = stmt.where(Bug.found_version_id == found_version_id)
    if requirement_id:
        if requirement_id == FILTER_EMPTY:
            stmt = stmt.where(
                not_(Bug.id.in_(select(BugRequirementLink.bug_id).distinct()))
            )
        else:
            stmt = stmt.where(
                Bug.id.in_(
                    select(BugRequirementLink.bug_id).where(
                        BugRequirementLink.requirement_id == requirement_id
                    )
                )
            )
    if plan_id:
        if plan_id == FILTER_EMPTY:
            stmt = stmt.where(not_(Bug.id.in_(select(BugPlanLink.bug_id).distinct())))
        else:
            stmt = stmt.where(
                Bug.id.in_(select(BugPlanLink.bug_id).where(BugPlanLink.plan_id == plan_id))
            )
    if q and q.strip():
        stmt = stmt.where(Bug.title.contains(q.strip()))

    return apply_custom_field_filters(
        stmt,
        custom_fields_col=Bug.custom_fields,
        template_fields=template_fields,
        custom_filters=custom_filters,
    )
