from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bug import BugFollowerLink


class BugFollowerScheduleError(ValueError):
    pass


def _is_schedule_participating(link: BugFollowerLink) -> bool:
    return (
        link.fix_estimate_points is not None
        or link.scheduled_start is not None
        or link.scheduled_end is not None
    )


async def get_bug_follower_link_or_raise(
    db: AsyncSession,
    bug_id: str,
    user_id: str,
) -> BugFollowerLink:
    result = await db.execute(
        select(BugFollowerLink).where(
            BugFollowerLink.bug_id == bug_id,
            BugFollowerLink.user_id == user_id,
        )
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise BugFollowerScheduleError("User is not a follower of this bug")
    return link


async def update_bug_follower_schedule(
    db: AsyncSession,
    link: BugFollowerLink,
    *,
    fix_estimate_points: Optional[float] = None,
    clear_estimate: bool = False,
    scheduled_start: Optional[date] = None,
    scheduled_end: Optional[date] = None,
    clear_schedule: bool = False,
    fields_set: set[str],
) -> None:
    if "fix_estimate_points" in fields_set:
        if clear_estimate:
            link.fix_estimate_points = None
        elif fix_estimate_points is not None:
            if fix_estimate_points < 0:
                raise BugFollowerScheduleError("fix_estimate_points must be >= 0")
            link.fix_estimate_points = fix_estimate_points

    if clear_schedule:
        link.scheduled_start = None
        link.scheduled_end = None
    else:
        if "scheduled_start" in fields_set:
            link.scheduled_start = scheduled_start
        if "scheduled_end" in fields_set:
            link.scheduled_end = scheduled_end

    start = link.scheduled_start
    end = link.scheduled_end
    if start is not None and end is not None and start > end:
        raise BugFollowerScheduleError("scheduled_start must be <= scheduled_end")
    if (start is None) != (end is None):
        pass
