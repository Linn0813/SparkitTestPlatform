from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Select, not_, or_, select

from app.models.case import TestCase
from app.models.requirement import CaseRequirementLink
from app.services.custom_field_filters import (
    FILTER_EMPTY,
    apply_custom_field_filters,
)
from app.services.list_filter_utils import apply_scalar_in, parse_csv_filter, split_empty_values

__all__ = ["FILTER_EMPTY", "apply_case_list_filters"]


def _apply_requirement_filter(stmt: Select, raw: Optional[str]) -> Select:
    values = parse_csv_filter(raw)
    if not values:
        return stmt
    has_empty, req_ids = split_empty_values(values)
    clauses = []
    if has_empty:
        clauses.append(not_(TestCase.id.in_(select(CaseRequirementLink.case_id).distinct())))
    if req_ids:
        clauses.append(
            TestCase.id.in_(
                select(CaseRequirementLink.case_id).where(
                    CaseRequirementLink.requirement_id.in_(req_ids)
                )
            )
        )
    if len(clauses) == 1:
        return stmt.where(clauses[0])
    return stmt.where(or_(*clauses))


def apply_case_list_filters(
    stmt: Select,
    *,
    q: Optional[str] = None,
    priority: Optional[str] = None,
    requirement_id: Optional[str] = None,
    template_fields: list[dict[str, Any]],
    custom_filters: Optional[dict[str, list[str]]] = None,
) -> Select:
    if q and q.strip():
        stmt = stmt.where(TestCase.title.contains(q.strip()))
    stmt = apply_scalar_in(stmt, TestCase.priority, priority)
    stmt = _apply_requirement_filter(stmt, requirement_id)
    return apply_custom_field_filters(
        stmt,
        custom_fields_col=TestCase.custom_fields,
        template_fields=template_fields,
        custom_filters=custom_filters,
    )
