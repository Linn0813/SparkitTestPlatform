from __future__ import annotations

from sqlalchemy import case

from app.services.custom_field_filters import extract_custom

SEVERITY_FIELD_ID = "field_severity"
SEVERITY_SORT_LABELS = ("致命", "严重", "一般", "轻微")


def bug_severity_rank_column(custom_fields_col):
    """Return sort rank column: 致命=1 … 轻微=4, unknown/empty last."""
    severity = extract_custom(custom_fields_col, SEVERITY_FIELD_ID)
    whens = {label: idx for idx, label in enumerate(SEVERITY_SORT_LABELS, start=1)}
    return case(whens, value=severity, else_=len(SEVERITY_SORT_LABELS) + 1)
