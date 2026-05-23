from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Select

from app.models.bug import Bug, BugFollowerLink
from app.models.requirement import BugPlanLink, BugRequirementLink
from app.services.custom_field_filters import (
    FILTER_EMPTY,
    apply_custom_field_filters,
    parse_custom_filters,
)
from app.services.list_filter_utils import (
    apply_created_date,
    apply_follower_in_or_empty,
    apply_link_in_or_empty,
    apply_nullable_fk_in_or_empty,
    apply_scalar_in,
    apply_scalar_not_in,
)

__all__ = ["FILTER_EMPTY", "parse_custom_filters", "apply_bug_list_filters"]


def apply_bug_list_filters(
    stmt: Select,
    *,
    status_key: Optional[str] = None,
    exclude_status_key: Optional[str] = None,
    assignee_id: Optional[str] = None,
    reporter_id: Optional[str] = None,
    follower_id: Optional[str] = None,
    plan_version_id: Optional[str] = None,
    found_version_id: Optional[str] = None,
    requirement_id: Optional[str] = None,
    plan_id: Optional[str] = None,
    q: Optional[str] = None,
    created_date: Optional[str] = None,
    template_fields: list[dict[str, Any]],
    custom_filters: Optional[dict[str, list[str]]] = None,
) -> Select:
    stmt = apply_scalar_in(stmt, Bug.status_key, status_key)
    stmt = apply_scalar_not_in(stmt, Bug.status_key, exclude_status_key)
    stmt = apply_nullable_fk_in_or_empty(stmt, Bug.assignee_id, assignee_id)
    stmt = apply_scalar_in(stmt, Bug.reporter_id, reporter_id)
    stmt = apply_follower_in_or_empty(stmt, Bug.id, BugFollowerLink, follower_id)
    stmt = apply_nullable_fk_in_or_empty(stmt, Bug.plan_version_id, plan_version_id)
    stmt = apply_nullable_fk_in_or_empty(stmt, Bug.found_version_id, found_version_id)
    stmt = apply_link_in_or_empty(
        stmt, Bug.id, BugRequirementLink, BugRequirementLink.requirement_id, requirement_id
    )
    stmt = apply_link_in_or_empty(stmt, Bug.id, BugPlanLink, BugPlanLink.plan_id, plan_id)
    if q and q.strip():
        stmt = stmt.where(Bug.title.contains(q.strip()))
    stmt = apply_created_date(stmt, Bug.created_at, created_date)

    return apply_custom_field_filters(
        stmt,
        custom_fields_col=Bug.custom_fields,
        template_fields=template_fields,
        custom_filters=custom_filters,
    )
