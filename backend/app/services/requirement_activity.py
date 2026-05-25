from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.requirement import RequirementActivity


async def log_requirement_activity(
    db: AsyncSession,
    *,
    requirement_id: str,
    actor_id: str,
    action_type: str,
    summary: str,
    detail: dict | None = None,
) -> RequirementActivity:
    row = RequirementActivity(
        requirement_id=requirement_id,
        actor_id=actor_id,
        action_type=action_type,
        summary=summary,
        detail=detail or {},
    )
    db.add(row)
    await db.flush()
    return row
