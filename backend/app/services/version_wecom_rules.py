from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.version_nodes import VERSION_WECOM_EVENT_KEYS
from app.models.version_workflow import VersionWecomNotifyRule
from app.services.version_wecom_defaults import DEFAULT_VERSION_WECOM_TEMPLATES


async def ensure_project_version_wecom_rules(project_id: str, db: AsyncSession) -> None:
    result = await db.execute(
        select(VersionWecomNotifyRule.event_key).where(
            VersionWecomNotifyRule.project_id == project_id
        )
    )
    existing = {row[0] for row in result.all()}
    for event_key in VERSION_WECOM_EVENT_KEYS:
        if event_key in existing:
            continue
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
