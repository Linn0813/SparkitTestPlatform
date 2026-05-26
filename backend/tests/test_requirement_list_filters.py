"""Unit tests for requirement list filter SQL helpers."""

from __future__ import annotations

from sqlalchemy import select

from app.models.requirement import Requirement
from app.services.requirement_filters import apply_requirement_list_filters


def _stmt_sql(stmt) -> str:
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


def test_apply_requirement_list_filters_title_q():
    base = select(Requirement).where(Requirement.project_id == "proj-1")
    stmt = apply_requirement_list_filters(base, q="登录")
    sql = _stmt_sql(stmt)
    assert "requirements.title" in sql.lower()
    assert "登录" in sql


def test_apply_requirement_list_filters_multi_status_or():
    base = select(Requirement).where(Requirement.project_id == "proj-1")
    stmt = apply_requirement_list_filters(base, status="draft,testing")
    sql = _stmt_sql(stmt)
    assert "requirements.status" in sql.lower()
    assert "draft" in sql
    assert "testing" in sql


def test_apply_requirement_list_filters_version_empty():
    base = select(Requirement).where(Requirement.project_id == "proj-1")
    stmt = apply_requirement_list_filters(base, version_id="__empty__")
    sql = _stmt_sql(stmt)
    assert "version_id" in sql.lower()
    assert "IS NULL" in sql.upper() or "is null" in sql.lower()


def test_apply_requirement_list_filters_developer_id():
    base = select(Requirement).where(Requirement.project_id == "proj-1")
    stmt = apply_requirement_list_filters(base, developer_id="user-a,user-b")
    sql = _stmt_sql(stmt)
    assert "frontend_rd_id" in sql.lower()
    assert "backend_rd_id" in sql.lower()
    assert "tech_owner_id" in sql.lower()
    assert "json_contains" in sql.lower()
    assert "user-a" in sql
    assert "user-b" in sql


def test_apply_requirement_list_filters_dev_handoff_range():
    from datetime import date

    base = select(Requirement).where(Requirement.project_id == "proj-1")
    stmt = apply_requirement_list_filters(
        base,
        dev_handoff_from=date(2024, 11, 1),
        dev_handoff_to=date(2024, 11, 30),
    )
    sql = _stmt_sql(stmt)
    assert "requirement_node_tasks" in sql.lower()
    assert "frontend_dev" in sql
    assert "2024-11-01" in sql
    assert "2024-11-30" in sql
