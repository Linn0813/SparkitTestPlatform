from __future__ import annotations

from datetime import date, datetime

from app.models.project_version import ProjectVersion


def pick_default_version(
    versions: list[ProjectVersion],
    today: date | None = None,
) -> ProjectVersion | None:
    """默认版本：released_at >= today 中最近的一个；否则取最新版本。"""
    if not versions:
        return None
    ref = today or date.today()
    upcoming = [v for v in versions if v.released_at is not None and v.released_at >= ref]
    if upcoming:
        return min(upcoming, key=lambda v: v.released_at)  # type: ignore[arg-type, return-value]
    return max(
        versions,
        key=lambda v: (
            v.released_at or date.min,
            v.num,
            v.updated_at or datetime.min,
        ),
    )
