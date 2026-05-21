from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bug import Bug
from app.models.project_version import ProjectVersion
from app.models.requirement import Requirement


async def validate_version_id(
    db: AsyncSession, project_id: str, version_id: str | None
) -> None:
    if version_id is None:
        return
    row = await db.get(ProjectVersion, version_id)
    if not row or row.project_id != project_id:
        raise ValueError("Invalid version id for this project")


async def count_version_references(db: AsyncSession, version_id: str) -> int:
    bugs_plan = await db.execute(
        select(func.count()).select_from(Bug).where(Bug.plan_version_id == version_id)
    )
    bugs_found = await db.execute(
        select(func.count()).select_from(Bug).where(Bug.found_version_id == version_id)
    )
    reqs = await db.execute(
        select(func.count()).select_from(Requirement).where(Requirement.version_id == version_id)
    )
    return (bugs_plan.scalar() or 0) + (bugs_found.scalar() or 0) + (reqs.scalar() or 0)
