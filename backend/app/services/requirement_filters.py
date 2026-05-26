"""Requirement list query filters."""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Select, func, or_, select
from sqlalchemy.sql import ColumnElement

from app.constants.requirement_nodes import DEVELOPER_ROLE_KEYS, DEVELOPMENT_NODE_KEYS
from app.models.requirement import Requirement, RequirementNodeTask
from app.services.list_filter_utils import _or_where, apply_nullable_fk_in_or_empty, apply_scalar_in, parse_csv_filter


def _developer_role_json_contains(uid: str, role_key: str) -> ColumnElement:
    path = f"$.{role_key}"
    return func.json_contains(
        func.json_extract(Requirement.role_assignee_ids, path),
        func.json_quote(uid),
    )


def _developer_match_clause(uid: str) -> ColumnElement:
    clauses: list[ColumnElement] = [
        Requirement.frontend_rd_id == uid,
        Requirement.backend_rd_id == uid,
        Requirement.tech_owner_id == uid,
    ]
    for role_key in DEVELOPER_ROLE_KEYS:
        clauses.append(_developer_role_json_contains(uid, role_key))
    return or_(*clauses)


def _dev_handoff_subquery():
    per_node = (
        select(
            RequirementNodeTask.requirement_id.label("requirement_id"),
            func.max(RequirementNodeTask.scheduled_end).label("node_end"),
        )
        .where(RequirementNodeTask.node_key.in_(DEVELOPMENT_NODE_KEYS))
        .where(RequirementNodeTask.scheduled_end.isnot(None))
        .group_by(RequirementNodeTask.requirement_id, RequirementNodeTask.node_key)
    ).subquery()
    return (
        select(
            per_node.c.requirement_id.label("requirement_id"),
            func.max(per_node.c.node_end).label("dev_handoff_end"),
        )
        .group_by(per_node.c.requirement_id)
    ).subquery()


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
    developer_id: Optional[str] = None,
    dev_handoff_from: Optional[date] = None,
    dev_handoff_to: Optional[date] = None,
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

    developer_ids = parse_csv_filter(developer_id)
    if developer_ids:
        stmt = _or_where(stmt, [_developer_match_clause(uid) for uid in developer_ids])

    if dev_handoff_from is not None or dev_handoff_to is not None:
        handoff_sq = _dev_handoff_subquery()
        stmt = stmt.join(handoff_sq, Requirement.id == handoff_sq.c.requirement_id)
        if dev_handoff_from is not None:
            stmt = stmt.where(handoff_sq.c.dev_handoff_end >= dev_handoff_from)
        if dev_handoff_to is not None:
            stmt = stmt.where(handoff_sq.c.dev_handoff_end <= dev_handoff_to)

    return stmt
