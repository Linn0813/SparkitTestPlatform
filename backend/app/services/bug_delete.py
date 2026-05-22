from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bug import (
    Bug,
    BugActivity,
    BugAttachment,
    BugCaseLink,
    BugComment,
    BugFollowerLink,
    BugStatusHistory,
)
from app.models.requirement import BugPlanLink, BugRequirementLink


async def delete_bug_cascade(db: AsyncSession, bug: Bug) -> None:
    """删除缺陷及其全部关联数据（活动、评论、历史、附件、链接等）。"""
    bug_id = bug.id
    await db.execute(delete(BugActivity).where(BugActivity.bug_id == bug_id))
    await db.execute(delete(BugComment).where(BugComment.bug_id == bug_id))
    await db.execute(delete(BugStatusHistory).where(BugStatusHistory.bug_id == bug_id))
    await db.execute(delete(BugAttachment).where(BugAttachment.bug_id == bug_id))
    await db.execute(delete(BugFollowerLink).where(BugFollowerLink.bug_id == bug_id))
    await db.execute(delete(BugCaseLink).where(BugCaseLink.bug_id == bug_id))
    await db.execute(delete(BugRequirementLink).where(BugRequirementLink.bug_id == bug_id))
    await db.execute(delete(BugPlanLink).where(BugPlanLink.bug_id == bug_id))
    await db.delete(bug)
