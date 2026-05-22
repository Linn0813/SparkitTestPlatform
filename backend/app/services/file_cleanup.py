from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bug import Bug, BugAttachment, BugComment
from app.models.case import TestCase
from app.services.file_refs import file_keys_from_bug, file_keys_from_case, file_keys_from_comment_body
from app.services.file_storage import delete_object_safe

logger = logging.getLogger(__name__)


async def collect_project_inline_file_keys(
    db: AsyncSession,
    project_id: str,
    *,
    omit_bug_id: str | None = None,
    omit_case_id: str | None = None,
    bug_override: Bug | None = None,
    case_override: TestCase | None = None,
) -> set[str]:
    """项目内仍被引用的内联文件 object_key（描述、前置、步骤、自定义字段、评论正文）。"""
    keys: set[str] = set()
    bugs = await db.execute(select(Bug).where(Bug.project_id == project_id))
    bug_ids: list[str] = []
    for bug in bugs.scalars().all():
        if omit_bug_id and bug.id == omit_bug_id:
            continue
        bug_ids.append(bug.id)
        if bug_override and bug.id == bug_override.id:
            keys.update(file_keys_from_bug(bug_override))
        else:
            keys.update(file_keys_from_bug(bug))

    if bug_ids:
        comments = await db.execute(select(BugComment).where(BugComment.bug_id.in_(bug_ids)))
        for comment in comments.scalars().all():
            keys.update(file_keys_from_comment_body(comment.body))

    cases = await db.execute(
        select(TestCase).where(TestCase.project_id == project_id, TestCase.deleted.is_(False))
    )
    for case in cases.scalars().all():
        if omit_case_id and case.id == omit_case_id:
            continue
        if case_override and case.id == case_override.id:
            keys.update(file_keys_from_case(case_override))
        else:
            keys.update(file_keys_from_case(case))
    return keys


async def delete_unreferenced_keys(
    db: AsyncSession,
    project_id: str,
    candidate_keys: set[str],
    **collect_kwargs,
) -> None:
    if not candidate_keys:
        return
    still_used = await collect_project_inline_file_keys(db, project_id, **collect_kwargs)
    for key in candidate_keys - still_used:
        await delete_object_safe(db, key)


async def cleanup_after_bug_content_change(
    db: AsyncSession,
    project_id: str,
    bug: Bug,
    old_keys: set[str],
    new_keys: set[str],
) -> None:
    removed = old_keys - new_keys
    await delete_unreferenced_keys(db, project_id, removed, bug_override=bug)


async def cleanup_after_case_content_change(
    db: AsyncSession,
    project_id: str,
    case: TestCase,
    old_keys: set[str],
    new_keys: set[str],
) -> None:
    removed = old_keys - new_keys
    await delete_unreferenced_keys(db, project_id, removed, case_override=case)


async def cleanup_after_bug_deleted(db: AsyncSession, project_id: str, bug: Bug) -> None:
    inline_keys = file_keys_from_bug(bug)
    comments = await db.execute(select(BugComment).where(BugComment.bug_id == bug.id))
    for comment in comments.scalars().all():
        inline_keys.update(file_keys_from_comment_body(comment.body))
    await delete_unreferenced_keys(db, project_id, inline_keys, omit_bug_id=bug.id)
    atts = await db.execute(select(BugAttachment).where(BugAttachment.bug_id == bug.id))
    for att in atts.scalars().all():
        await delete_object_safe(db, att.object_key)


async def cleanup_after_case_deleted(db: AsyncSession, project_id: str, case: TestCase) -> None:
    inline_keys = file_keys_from_case(case)
    await delete_unreferenced_keys(db, project_id, inline_keys, omit_case_id=case.id)
