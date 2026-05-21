from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bug import BugActivity, BugStatusHistory
from app.models.template import BugStatus
from app.models.user import User
from app.schemas.user import UserOut


async def _bug_status_label_map(db: AsyncSession, project_id: str) -> dict[str, str]:
    result = await db.execute(select(BugStatus).where(BugStatus.project_id == project_id))
    return {s.key: s.label for s in result.scalars().all()}


def _status_display(labels: dict[str, str], key: str | None) -> str:
    if not key:
        return "—"
    return labels.get(key, key)


async def log_bug_activity(
    db: AsyncSession,
    *,
    bug_id: str,
    actor_id: str,
    action_type: str,
    summary: str,
    detail: dict | None = None,
) -> BugActivity:
    row = BugActivity(
        bug_id=bug_id,
        actor_id=actor_id,
        action_type=action_type,
        summary=summary,
        detail=detail or {},
    )
    db.add(row)
    await db.flush()
    return row


async def list_bug_activities_merged(db: AsyncSession, bug_id: str, *, project_id: str) -> list[dict]:
    """合并 bug_activities 与 bug_status_history，按时间倒序。"""
    status_labels = await _bug_status_label_map(db, project_id)
    activities = await db.execute(
        select(BugActivity).where(BugActivity.bug_id == bug_id).order_by(BugActivity.created_at.desc())
    )
    history = await db.execute(
        select(BugStatusHistory).where(BugStatusHistory.bug_id == bug_id).order_by(BugStatusHistory.created_at.desc())
    )
    items: list[dict] = []
    for a in activities.scalars().all():
        actor = await db.get(User, a.actor_id)
        items.append(
            {
                "id": a.id,
                "source": "activity",
                "action_type": a.action_type,
                "summary": a.summary,
                "detail": a.detail,
                "actor": UserOut.model_validate(actor) if actor else None,
                "created_at": a.created_at,
            }
        )
    for h in history.scalars().all():
        actor = await db.get(User, h.changed_by)
        from_label = _status_display(status_labels, h.from_status)
        to_label = _status_display(status_labels, h.to_status)
        summary = f"状态变更：{from_label} → {to_label}"
        items.append(
            {
                "id": h.id,
                "source": "status_history",
                "action_type": "status_change",
                "summary": summary,
                "detail": {"from_status": h.from_status, "to_status": h.to_status},
                "actor": UserOut.model_validate(actor) if actor else None,
                "created_at": h.created_at,
            }
        )
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return items
