from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.version_nodes import VERSION_WECOM_EVENT_KEYS
from app.models.version_workflow import VersionWecomNotifyRule
from app.services.version_wecom_defaults import DEFAULT_VERSION_WECOM_TEMPLATES


def _existing_event_keys(db: AsyncSession, project_id: str, persisted: set[str]) -> set[str]:
    keys = set(persisted)
    for obj in db.new:
        if isinstance(obj, VersionWecomNotifyRule) and obj.project_id == project_id:
            keys.add(obj.event_key)
    return keys


async def ensure_project_version_wecom_rules(project_id: str, db: AsyncSession) -> None:
    result = await db.execute(
        select(VersionWecomNotifyRule.event_key).where(
            VersionWecomNotifyRule.project_id == project_id
        )
    )
    persisted = {row[0] for row in result.all()}
    existing = _existing_event_keys(db, project_id, persisted)

    for event_key in VERSION_WECOM_EVENT_KEYS:
        if event_key in existing:
            continue
        row = await db.execute(
            select(VersionWecomNotifyRule.id)
            .where(
                VersionWecomNotifyRule.project_id == project_id,
                VersionWecomNotifyRule.event_key == event_key,
            )
            .limit(1)
        )
        if row.scalar_one_or_none():
            existing.add(event_key)
            continue
        try:
            async with db.begin_nested():
                db.add(
                    VersionWecomNotifyRule(
                        project_id=project_id,
                        event_key=event_key,
                        message_template=DEFAULT_VERSION_WECOM_TEMPLATES[event_key],
                        notify_user_ids=[],
                        enabled=True,
                    )
                )
                await db.flush()
            existing.add(event_key)
        except IntegrityError:
            existing.add(event_key)
