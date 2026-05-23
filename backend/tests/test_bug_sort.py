"""Unit tests for bug list sort helpers."""

from __future__ import annotations

from app.services.bug_sort import SEVERITY_SORT_LABELS, bug_severity_rank_column


def test_severity_sort_labels_order():
    assert SEVERITY_SORT_LABELS == ("致命", "严重", "一般", "轻微")


def test_bug_severity_rank_column_compiles():
    from sqlalchemy import column, select

    rank = bug_severity_rank_column(column("custom_fields"))
    compiled = str(select(column("id")).order_by(rank.asc()).compile(compile_kwargs={"literal_binds": True}))
    assert "CASE" in compiled.upper()
    assert "致命" in compiled
