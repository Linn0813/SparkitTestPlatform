from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bug import BugFollowerLink
from app.models.project import ProjectMember
from app.models.plan import TestPlan
from app.models.requirement import BugPlanLink, BugRequirementLink, CaseRequirementLink
from app.models.requirement import Requirement as ReqModel


async def set_case_requirements(db: AsyncSession, case_id: str, requirement_ids: list[str]) -> None:
    await db.execute(delete(CaseRequirementLink).where(CaseRequirementLink.case_id == case_id))
    for rid in requirement_ids:
        db.add(CaseRequirementLink(case_id=case_id, requirement_id=rid))


async def get_case_requirement_ids(db: AsyncSession, case_id: str) -> list[str]:
    result = await db.execute(
        select(CaseRequirementLink.requirement_id).where(CaseRequirementLink.case_id == case_id)
    )
    return list(result.scalars().all())


async def set_bug_requirements(db: AsyncSession, bug_id: str, requirement_ids: list[str]) -> None:
    await db.execute(delete(BugRequirementLink).where(BugRequirementLink.bug_id == bug_id))
    for rid in requirement_ids:
        db.add(BugRequirementLink(bug_id=bug_id, requirement_id=rid))


async def get_bug_requirement_ids(db: AsyncSession, bug_id: str) -> list[str]:
    result = await db.execute(
        select(BugRequirementLink.requirement_id).where(BugRequirementLink.bug_id == bug_id)
    )
    return list(result.scalars().all())


async def set_bug_plans(db: AsyncSession, bug_id: str, plan_ids: list[str]) -> None:
    await db.execute(delete(BugPlanLink).where(BugPlanLink.bug_id == bug_id))
    for pid in plan_ids:
        db.add(BugPlanLink(bug_id=bug_id, plan_id=pid))


async def get_bug_plan_ids(db: AsyncSession, bug_id: str) -> list[str]:
    result = await db.execute(select(BugPlanLink.plan_id).where(BugPlanLink.bug_id == bug_id))
    return list(result.scalars().all())


async def validate_requirement_ids(db: AsyncSession, project_id: str, ids: list[str]) -> None:
    if not ids:
        return
    result = await db.execute(
        select(ReqModel.id).where(ReqModel.project_id == project_id, ReqModel.id.in_(ids))
    )
    found = set(result.scalars().all())
    if len(found) != len(set(ids)):
        raise ValueError("Invalid requirement ids for project")


async def set_bug_followers(db: AsyncSession, bug_id: str, user_ids: list[str]) -> None:
    desired = list(dict.fromkeys(user_ids))
    result = await db.execute(
        select(BugFollowerLink).where(BugFollowerLink.bug_id == bug_id)
    )
    existing = {link.user_id: link for link in result.scalars().all()}
    desired_set = set(desired)

    for uid, link in existing.items():
        if uid not in desired_set:
            await db.delete(link)

    for uid in desired:
        if uid not in existing:
            db.add(BugFollowerLink(bug_id=bug_id, user_id=uid))


async def get_bug_follower_ids(db: AsyncSession, bug_id: str) -> list[str]:
    result = await db.execute(
        select(BugFollowerLink.user_id).where(BugFollowerLink.bug_id == bug_id)
    )
    return list(result.scalars().all())


async def validate_project_member_ids(
    db: AsyncSession, project_id: str, ids: list[str]
) -> None:
    if not ids:
        return
    result = await db.execute(
        select(ProjectMember.user_id).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id.in_(ids)
        )
    )
    found = set(result.scalars().all())
    if len(found) != len(set(ids)):
        raise ValueError("Invalid project member user ids")


async def validate_plan_ids(db: AsyncSession, project_id: str, ids: list[str]) -> None:
    if not ids:
        return
    result = await db.execute(
        select(TestPlan.id).where(TestPlan.project_id == project_id, TestPlan.id.in_(ids))
    )
    found = set(result.scalars().all())
    if len(found) != len(set(ids)):
        raise ValueError("Invalid plan ids for project")
