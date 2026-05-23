from __future__ import annotations

import json
from typing import Optional, Union

from sqlalchemy import func, or_
from sqlalchemy.sql import ColumnElement

FILTER_EMPTY = "__empty__"

FilterValues = Union[str, list[str]]


def _like_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _json_path(field_id: str) -> str:
    return f'$."{field_id}"'


def extract_custom(custom_fields_col, field_id: str):
    return func.json_unquote(func.json_extract(custom_fields_col, _json_path(field_id)))


def custom_field_empty_clause(custom_fields_col, field_id: str, field_type: str) -> ColumnElement:
    raw = func.json_extract(custom_fields_col, _json_path(field_id))
    unquoted = extract_custom(custom_fields_col, field_id)
    parts: list[ColumnElement] = [raw.is_(None), unquoted.is_(None), unquoted == ""]
    if field_type in ("select", "member", "number", "date"):
        parts.append(unquoted == "null")
    if field_type == "multi_select":
        parts.append(raw == "[]")
        parts.append(unquoted == "[]")
    if field_type == "switch":
        parts.append(raw.is_(None))
    if field_type in ("text", "textarea"):
        parts.extend([unquoted == "", unquoted.is_(None)])
    if field_type == "richtext":
        parts.append(unquoted == '{"text": "", "files": []}')
    return or_(*parts)


def custom_field_match_clause(
    custom_fields_col, field_id: str, field_type: str, value: str
) -> ColumnElement:
    raw = func.json_extract(custom_fields_col, _json_path(field_id))
    unquoted = extract_custom(custom_fields_col, field_id)
    if field_type == "multi_select":
        return func.json_contains(raw, func.json_quote(value))
    if field_type == "switch":
        want = "true" if value in ("1", "true", "True", "yes") else "false"
        return unquoted == want
    if field_type in ("text", "textarea"):
        return unquoted.like(_like_pattern(value), escape="\\")
    return unquoted == value


def normalize_filter_values(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        seen: set[str] = set()
        out: list[str] = []
        for item in value:
            s = str(item).strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)
        return out
    if isinstance(value, str):
        from app.services.list_filter_utils import parse_csv_filter

        return parse_csv_filter(value)
    s = str(value).strip()
    return [s] if s else []


def parse_custom_filters(raw: Optional[str]) -> dict[str, list[str]]:
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid custom_filters JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("custom_filters must be a JSON object")
    out: dict[str, list[str]] = {}
    for k, v in data.items():
        if not isinstance(k, str) or not k:
            continue
        values = normalize_filter_values(v)
        if values:
            out[k] = values
    return out


def apply_custom_field_filters(
    stmt,
    *,
    custom_fields_col,
    template_fields: list[dict],
    custom_filters: Optional[dict[str, list[str]]] = None,
):
    if not custom_filters or not template_fields:
        return stmt
    field_by_id = {f["id"]: f for f in template_fields}
    for field_id, values in custom_filters.items():
        field = field_by_id.get(field_id)
        if not field or not values:
            continue
        ftype = field.get("type") or "text"
        has_empty = FILTER_EMPTY in values
        rest = [v for v in values if v != FILTER_EMPTY]
        clauses: list[ColumnElement] = []
        if has_empty:
            clauses.append(custom_field_empty_clause(custom_fields_col, field_id, ftype))
        for val in rest:
            clauses.append(custom_field_match_clause(custom_fields_col, field_id, ftype, val))
        if not clauses:
            continue
        if len(clauses) == 1:
            stmt = stmt.where(clauses[0])
        else:
            stmt = stmt.where(or_(*clauses))
    return stmt
