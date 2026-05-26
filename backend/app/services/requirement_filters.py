"""Requirement list query filters."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Select

from app.models.requirement import Requirement
from app.services.list_filter_utils import apply_nullable_fk_in_or_empty, apply_scalar_in


def apply_requirement_list_filters(
    stmt: Select,
    *,
    q: Optional[str] = None,
    version_id: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    req_type: Optional[str] = None,
    frontend_rd_id: Optional[str] = None,
    backend_rd_id: Optional[str] = None,
    pm_id: Optional[str] = None,
    qa_id: Optional[str] = None,
) -> Select:
    keyword = (q or "").strip()
    if keyword:
        stmt = stmt.where(Requirement.title.ilike(f"%{keyword}%"))

    if version_id is not None and str(version_id).strip():
        stmt = apply_nullable_fk_in_or_empty(stmt, Requirement.version_id, version_id)

    stmt = apply_scalar_in(stmt, Requirement.status, status)
    stmt = apply_scalar_in(stmt, Requirement.priority, priority)
    stmt = apply_scalar_in(stmt, Requirement.req_type, req_type)

    if frontend_rd_id is not None:
        stmt = stmt.where(Requirement.frontend_rd_id == frontend_rd_id)
    if backend_rd_id is not None:
        stmt = stmt.where(Requirement.backend_rd_id == backend_rd_id)
    if pm_id is not None:
        stmt = stmt.where(Requirement.pm_id == pm_id)
    if qa_id is not None:
        stmt = stmt.where(Requirement.qa_id == qa_id)

    return stmt
