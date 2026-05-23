"""Unit tests for list filter CSV / custom filter parsing."""

from __future__ import annotations

import pytest
from datetime import datetime

from app.services.custom_field_filters import FILTER_EMPTY, normalize_filter_values, parse_custom_filters
from app.services.list_filter_utils import (
    parse_created_date_bounds,
    parse_csv_filter,
    split_empty_values,
)


def test_parse_csv_filter_single():
    assert parse_csv_filter("fixed") == ["fixed"]


def test_parse_csv_filter_multiple():
    assert parse_csv_filter("fixed,accepted, fixed") == ["fixed", "accepted"]


def test_parse_csv_filter_empty():
    assert parse_csv_filter(None) == []
    assert parse_csv_filter("") == []
    assert parse_csv_filter("  ") == []


def test_split_empty_values():
    has_empty, rest = split_empty_values(["a", FILTER_EMPTY, "b"])
    assert has_empty is True
    assert rest == ["a", "b"]


def test_normalize_filter_values_from_list():
    assert normalize_filter_values(["致命", "严重", "致命"]) == ["致命", "严重"]


def test_parse_custom_filters_array_values():
    payload = '{"field_severity": ["致命", "严重"], "field_x": "一般"}'
    parsed = parse_custom_filters(payload)
    assert parsed == {"field_severity": ["致命", "严重"], "field_x": ["一般"]}


def test_parse_custom_filters_with_empty_marker():
    payload = f'{{"field_severity": ["{FILTER_EMPTY}", "致命"]}}'
    parsed = parse_custom_filters(payload)
    assert parsed["field_severity"] == [FILTER_EMPTY, "致命"]


def test_parse_custom_filters_invalid_json():
    with pytest.raises(ValueError, match="invalid custom_filters JSON"):
        parse_custom_filters("not-json")


def test_parse_created_date_bounds_utc8_day():
    start, end = parse_created_date_bounds("2026-05-21")
    assert start.isoformat() == "2026-05-20T16:00:00"
    assert end.isoformat() == "2026-05-21T16:00:00"


def test_parse_created_date_bounds_includes_utc8_midnight():
    start, end = parse_created_date_bounds("2026-05-21")
    # UTC 2026-05-20 16:00 = UTC+8 2026-05-21 00:00
    assert start <= datetime.fromisoformat("2026-05-20T16:00:00")
    # UTC 2026-05-21 15:59:59 = UTC+8 2026-05-21 23:59:59
    assert end > datetime.fromisoformat("2026-05-21T15:59:59")
    assert end <= datetime.fromisoformat("2026-05-21T16:00:00")


def test_apply_scalar_not_in():
    from sqlalchemy import column, select

    from app.services.list_filter_utils import apply_scalar_not_in

    stmt = apply_scalar_not_in(select(column("status")), column("status"), "rejected,suspended")
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "NOT IN" in compiled.upper()
    assert "rejected" in compiled
    assert "suspended" in compiled


def test_apply_scalar_not_in_empty():
    from sqlalchemy import column, select

    from app.services.list_filter_utils import apply_scalar_not_in

    base = select(column("status"))
    stmt = apply_scalar_not_in(base, column("status"), None)
    assert str(stmt.compile()) == str(base.compile())


def test_parse_created_date_bounds_invalid():
    with pytest.raises(ValueError, match="invalid created_date"):
        parse_created_date_bounds("2026/05/21")
