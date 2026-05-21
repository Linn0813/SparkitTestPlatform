from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Select, not_, select

from app.models.case import TestCase
from app.models.requirement import CaseRequirementLink
from app.services.custom_field_filters import (
    FILTER_EMPTY,
    apply_custom_field_filters,
)

__all__ = ["FILTER_EMPTY", "apply_case_list_filters"]


def apply_case_list_filters(
    stmt: Select,
    *,
    q: Optional[str] = None,
    priority: Optional[str] = None,
    requirement_id: Optional[str] = None,
    template_fields: list[dict[str, Any]],
    custom_filters: Optional[dict[str, str]] = None,
) -> Select:
    if q and q.strip():
        stmt = stmt.where(TestCase.title.contains(q.strip()))
    if priority:
        stmt = stmt.where(TestCase.priority == priority)
    if requirement_id:
        if requirement_id == FILTER_EMPTY:
            stmt = stmt.where(
                not_(TestCase.id.in_(select(CaseRequirementLink.case_id).distinct()))
            )
        else:
            stmt = stmt.where(
                TestCase.id.in_(
                    select(CaseRequirementLink.case_id).where(
                        CaseRequirementLink.requirement_id == requirement_id
                    )
                )
            )
    return apply_custom_field_filters(
        stmt,
        custom_fields_col=TestCase.custom_fields,
        template_fields=template_fields,
        custom_filters=custom_filters,
    )
