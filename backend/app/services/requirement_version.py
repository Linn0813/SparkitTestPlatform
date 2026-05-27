from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.models.requirement import Requirement

CONFLICT_DETAIL = "需求已被他人更新，请刷新后重试"


def _normalize_updated_at(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.replace(microsecond=0)


def assert_requirement_version(row: Requirement, expected: datetime | None) -> None:
    """乐观锁：expected 与 row.updated_at 不一致时拒绝写入。"""
    if expected is None:
        return
    current = row.updated_at
    if current is None:
        return
    if _normalize_updated_at(current) != _normalize_updated_at(expected):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=CONFLICT_DETAIL)
