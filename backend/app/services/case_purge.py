from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bug import BugCaseLink
from app.models.case import TestCase
from app.models.plan import PlanCase, PlanCaseResult
from app.models.requirement import CaseRequirementLink
from app.services.file_cleanup import cleanup_after_case_deleted


async def hard_delete_test_cases(
    db: AsyncSession,
    project_id: str,
    cases: list[TestCase],
) -> None:
    """物理删除用例及其关联（用于模块删除前清理已软删用例）。"""
    if not cases:
        return
    case_ids = [c.id for c in cases]
    plan_case_ids_sq = select(PlanCase.id).where(PlanCase.case_id.in_(case_ids))
    await db.execute(delete(PlanCaseResult).where(PlanCaseResult.plan_case_id.in_(plan_case_ids_sq)))
    await db.execute(delete(PlanCase).where(PlanCase.case_id.in_(case_ids)))
    await db.execute(delete(CaseRequirementLink).where(CaseRequirementLink.case_id.in_(case_ids)))
    await db.execute(delete(BugCaseLink).where(BugCaseLink.case_id.in_(case_ids)))
    for case in cases:
        await cleanup_after_case_deleted(db, project_id, case)
        await db.delete(case)
    await db.flush()
