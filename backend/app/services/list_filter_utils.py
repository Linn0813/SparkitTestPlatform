from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import Select, not_, or_, select
from sqlalchemy.sql import ColumnElement

from app.services.custom_field_filters import FILTER_EMPTY

UTC8 = ZoneInfo("Asia/Shanghai")

__all__ = [
    "FILTER_EMPTY",
    "parse_csv_filter",
    "split_empty_values",
    "parse_created_date_bounds",
    "apply_created_date",
    "apply_scalar_in",
    "apply_scalar_not_in",
    "apply_nullable_fk_in_or_empty",
    "apply_follower_in_or_empty",
    "apply_link_in_or_empty",
]


def parse_csv_filter(raw: Optional[str]) -> list[str]:
    if not raw or not str(raw).strip():
        return []
    seen: set[str] = set()
    out: list[str] = []
    for part in str(raw).split(","):
        value = part.strip()
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def split_empty_values(values: list[str]) -> tuple[bool, list[str]]:
    has_empty = FILTER_EMPTY in values
    rest = [v for v in values if v != FILTER_EMPTY]
    return has_empty, rest


def parse_created_date_bounds(date_str: str) -> tuple[datetime, datetime]:
    """Parse YYYY-MM-DD as a calendar day in UTC+8; return UTC naive [start, next_day_start)."""
    raw = date_str.strip()
    try:
        day = date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"invalid created_date: {raw!r}, expected YYYY-MM-DD") from exc
    start_local = datetime.combine(day, time.min, tzinfo=UTC8)
    end_local = start_local + timedelta(days=1)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc


def apply_created_date(stmt: Select, column, date_str: Optional[str]) -> Select:
    if not date_str or not date_str.strip():
        return stmt
    start, end = parse_created_date_bounds(date_str)
    return stmt.where(column >= start, column < end)


def _or_where(stmt: Select, clauses: list[ColumnElement]) -> Select:
    if not clauses:
        return stmt
    if len(clauses) == 1:
        return stmt.where(clauses[0])
    return stmt.where(or_(*clauses))


def apply_scalar_in(stmt: Select, column, raw: Optional[str]) -> Select:
    values = parse_csv_filter(raw)
    if not values:
        return stmt
    _, ids = split_empty_values(values)
    if not ids:
        return stmt
    return stmt.where(column.in_(ids))


def apply_scalar_not_in(stmt: Select, column, raw: Optional[str]) -> Select:
    values = parse_csv_filter(raw)
    if not values:
        return stmt
    _, ids = split_empty_values(values)
    if not ids:
        return stmt
    return stmt.where(column.notin_(ids))


def apply_nullable_fk_in_or_empty(stmt: Select, column, raw: Optional[str]) -> Select:
    values = parse_csv_filter(raw)
    if not values:
        return stmt
    has_empty, ids = split_empty_values(values)
    clauses: list[ColumnElement] = []
    if has_empty:
        clauses.append(column.is_(None))
    if ids:
        clauses.append(column.in_(ids))
    return _or_where(stmt, clauses)


def apply_follower_in_or_empty(stmt: Select, bug_id_col, follower_link_model, raw: Optional[str]) -> Select:
    values = parse_csv_filter(raw)
    if not values:
        return stmt
    has_empty, user_ids = split_empty_values(values)
    clauses: list[ColumnElement] = []
    if has_empty:
        clauses.append(not_(bug_id_col.in_(select(follower_link_model.bug_id).distinct())))
    if user_ids:
        clauses.append(
            bug_id_col.in_(
                select(follower_link_model.bug_id).where(follower_link_model.user_id.in_(user_ids))
            )
        )
    return _or_where(stmt, clauses)


def apply_link_in_or_empty(
    stmt: Select,
    entity_id_col,
    link_model,
    link_entity_col,
    raw: Optional[str],
) -> Select:
    values = parse_csv_filter(raw)
    if not values:
        return stmt
    has_empty, entity_ids = split_empty_values(values)
    clauses: list[ColumnElement] = []
    if has_empty:
        clauses.append(not_(entity_id_col.in_(select(link_model.bug_id).distinct())))
    if entity_ids:
        clauses.append(
            entity_id_col.in_(
                select(link_model.bug_id).where(link_entity_col.in_(entity_ids))
            )
        )
    return _or_where(stmt, clauses)
