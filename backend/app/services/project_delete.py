from __future__ import annotations

from sqlalchemy import delete, select, update
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
from app.models.case import CaseModule, TestCase
from app.models.plan import PlanCase, PlanCaseResult, TestPlan
from app.models.project import Project, ProjectMember
from app.models.project_version import ProjectVersion
from app.models.requirement import (
    BugPlanLink,
    BugRequirementLink,
    CaseRequirementLink,
    Requirement,
    RequirementActivity,
    RequirementComment,
    RequirementNodeProgress,
)
from app.models.stored_file import StoredFile
from app.models.template import BugStatus, ProjectFieldTemplate, ProjectIntegration, RequirementWorkflowNodeDef
from app.models.user import User
from app.models.version_workflow import VersionWecomNotifyRule
from app.models.wecom_rule import BugWecomNotifyRule
from app.services.file_refs import (
    file_keys_from_bug,
    file_keys_from_case,
    file_keys_from_comment_body,
)
from app.services.file_storage import delete_object_safe


async def _collect_file_keys(db: AsyncSession, project_id: str) -> set[str]:
    keys: set[str] = set()
    prefix = f"projects/{project_id}/"
    stored = await db.execute(
        select(StoredFile.storage_key).where(StoredFile.storage_key.startswith(prefix))
    )
    keys.update(row[0] for row in stored.all())

    bugs = await db.execute(select(Bug).where(Bug.project_id == project_id))
    bug_list = bugs.scalars().all()
    bug_ids = [b.id for b in bug_list]
    for bug in bug_list:
        keys.update(file_keys_from_bug(bug))

    if bug_ids:
        comments = await db.execute(select(BugComment).where(BugComment.bug_id.in_(bug_ids)))
        for comment in comments.scalars().all():
            keys.update(file_keys_from_comment_body(comment.body))
        atts = await db.execute(select(BugAttachment.object_key).where(BugAttachment.bug_id.in_(bug_ids)))
        keys.update(row[0] for row in atts.all())

    cases = await db.execute(select(TestCase).where(TestCase.project_id == project_id))
    for case in cases.scalars().all():
        keys.update(file_keys_from_case(case))

    return keys


async def _delete_stored_files(db: AsyncSession, keys: set[str]) -> None:
    for key in keys:
        await delete_object_safe(db, key)


async def _delete_plan_data(db: AsyncSession, project_id: str) -> None:
    plan_ids_sq = select(TestPlan.id).where(TestPlan.project_id == project_id)
    pc_ids_sq = select(PlanCase.id).where(PlanCase.plan_id.in_(plan_ids_sq))

    await db.execute(delete(PlanCaseResult).where(PlanCaseResult.plan_case_id.in_(pc_ids_sq)))
    await db.execute(delete(PlanCase).where(PlanCase.plan_id.in_(plan_ids_sq)))

    bug_ids_sq = select(Bug.id).where(Bug.project_id == project_id)
    await db.execute(
        delete(BugPlanLink).where(
            (BugPlanLink.plan_id.in_(plan_ids_sq)) | (BugPlanLink.bug_id.in_(bug_ids_sq))
        )
    )
    await db.execute(delete(TestPlan).where(TestPlan.project_id == project_id))


async def _delete_bug_data(db: AsyncSession, project_id: str) -> None:
    bug_ids_sq = select(Bug.id).where(Bug.project_id == project_id)

    await db.execute(delete(BugActivity).where(BugActivity.bug_id.in_(bug_ids_sq)))
    await db.execute(delete(BugComment).where(BugComment.bug_id.in_(bug_ids_sq)))
    await db.execute(delete(BugStatusHistory).where(BugStatusHistory.bug_id.in_(bug_ids_sq)))
    await db.execute(delete(BugAttachment).where(BugAttachment.bug_id.in_(bug_ids_sq)))
    await db.execute(delete(BugFollowerLink).where(BugFollowerLink.bug_id.in_(bug_ids_sq)))
    await db.execute(delete(BugCaseLink).where(BugCaseLink.bug_id.in_(bug_ids_sq)))
    await db.execute(delete(BugRequirementLink).where(BugRequirementLink.bug_id.in_(bug_ids_sq)))
    await db.execute(delete(BugPlanLink).where(BugPlanLink.bug_id.in_(bug_ids_sq)))
    await db.execute(delete(Bug).where(Bug.project_id == project_id))


async def _delete_requirement_case_data(db: AsyncSession, project_id: str) -> None:
    case_ids_sq = select(TestCase.id).where(TestCase.project_id == project_id)
    req_ids_sq = select(Requirement.id).where(Requirement.project_id == project_id)

    await db.execute(
        delete(CaseRequirementLink).where(
            (CaseRequirementLink.case_id.in_(case_ids_sq))
            | (CaseRequirementLink.requirement_id.in_(req_ids_sq))
        )
    )
    await db.execute(delete(TestCase).where(TestCase.project_id == project_id))
    await db.execute(delete(RequirementComment).where(RequirementComment.requirement_id.in_(req_ids_sq)))
    await db.execute(delete(RequirementActivity).where(RequirementActivity.requirement_id.in_(req_ids_sq)))
    await db.execute(
        delete(RequirementNodeProgress).where(RequirementNodeProgress.requirement_id.in_(req_ids_sq))
    )
    await db.execute(delete(Requirement).where(Requirement.project_id == project_id))


async def _delete_case_modules(db: AsyncSession, project_id: str) -> None:
    while True:
        modules = await db.execute(select(CaseModule).where(CaseModule.project_id == project_id))
        rows = modules.scalars().all()
        if not rows:
            break
        ids = {m.id for m in rows}
        parent_ids = {m.parent_id for m in rows if m.parent_id}
        leaf_ids = [mid for mid in ids if mid not in parent_ids]
        if not leaf_ids:
            for m in rows:
                m.parent_id = None
            await db.flush()
            await db.execute(delete(CaseModule).where(CaseModule.project_id == project_id))
            break
        await db.execute(delete(CaseModule).where(CaseModule.id.in_(leaf_ids)))


async def _delete_project_meta(db: AsyncSession, project_id: str) -> None:
    await db.execute(delete(ProjectVersion).where(ProjectVersion.project_id == project_id))
    await db.execute(delete(BugWecomNotifyRule).where(BugWecomNotifyRule.project_id == project_id))
    await db.execute(delete(VersionWecomNotifyRule).where(VersionWecomNotifyRule.project_id == project_id))
    await db.execute(delete(ProjectIntegration).where(ProjectIntegration.project_id == project_id))
    await db.execute(delete(BugStatus).where(BugStatus.project_id == project_id))
    await db.execute(delete(RequirementWorkflowNodeDef).where(RequirementWorkflowNodeDef.project_id == project_id))
    await db.execute(delete(ProjectFieldTemplate).where(ProjectFieldTemplate.project_id == project_id))
    await db.execute(delete(ProjectMember).where(ProjectMember.project_id == project_id))


async def delete_project_cascade(db: AsyncSession, project: Project) -> None:
    project_id = project.id
    file_keys = await _collect_file_keys(db, project_id)

    await _delete_plan_data(db, project_id)
    await _delete_bug_data(db, project_id)
    await _delete_requirement_case_data(db, project_id)
    await _delete_case_modules(db, project_id)
    await _delete_project_meta(db, project_id)

    await db.execute(
        update(User).where(User.last_project_id == project_id).values(last_project_id=None)
    )

    await _delete_stored_files(db, file_keys)
    await db.delete(project)
    await db.flush()

