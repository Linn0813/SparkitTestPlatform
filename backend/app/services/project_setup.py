from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.template import (
    BugStatus,
    ProjectFieldTemplate,
    ProjectIntegration,
    RequirementOptionDef,
    RequirementRoleDef,
    RequirementWorkflowNodeDef,
    TemplateScene,
)
from app.services.requirement_config import ensure_project_option_defs, ensure_project_role_defs
from app.services.requirement_workflow import ensure_project_workflow_defs
from app.models.wecom_rule import BugWecomNotifyRule
from app.services.defaults import DEFAULT_BUG_FIELDS, DEFAULT_BUG_STATUSES, DEFAULT_CASE_FIELDS, DEFAULT_REQUIREMENT_FIELDS
from app.services.wecom_notify import DEFAULT_CREATE_TEMPLATE, DEFAULT_STATUS_TEMPLATE


async def ensure_project_defaults(project_id: str, db: AsyncSession) -> None:
    for scene, fields in (
        (TemplateScene.functional_case, DEFAULT_CASE_FIELDS),
        (TemplateScene.bug, DEFAULT_BUG_FIELDS),
        (TemplateScene.requirement, DEFAULT_REQUIREMENT_FIELDS),
    ):
        existing = await db.execute(
            select(ProjectFieldTemplate).where(
                ProjectFieldTemplate.project_id == project_id,
                ProjectFieldTemplate.scene == scene,
            )
        )
        tpl = existing.scalar_one_or_none()
        if not tpl:
            db.add(ProjectFieldTemplate(project_id=project_id, scene=scene, fields=fields))
        elif scene == TemplateScene.bug and fields and not tpl.fields:
            tpl.fields = fields
            await db.flush()

    status_result = await db.execute(select(BugStatus).where(BugStatus.project_id == project_id))
    if not status_result.scalars().first():
        for s in DEFAULT_BUG_STATUSES:
            db.add(
                BugStatus(
                    project_id=project_id,
                    key=s["key"],
                    label=s["label"],
                    sort=s["sort"],
                    is_terminal=s["is_terminal"],
                    notify_wecom=s["notify_wecom"],
                    notify_roles=s.get("notify_roles", ["reporter", "followers"]),
                )
            )

    integ = await db.execute(
        select(ProjectIntegration).where(ProjectIntegration.project_id == project_id)
    )
    integ_row = integ.scalar_one_or_none()
    if not integ_row:
        db.add(
            ProjectIntegration(
                project_id=project_id,
                wecom_enabled=False,
                status_notify_template=DEFAULT_STATUS_TEMPLATE,
                create_notify_template=DEFAULT_CREATE_TEMPLATE,
                notify_on_create=False,
            )
        )
        await db.flush()

    create_rule = await db.execute(
        select(BugWecomNotifyRule).where(
            BugWecomNotifyRule.project_id == project_id,
            BugWecomNotifyRule.kind == "create",
        )
    )
    if not create_rule.scalar_one_or_none():
        db.add(
            BugWecomNotifyRule(
                project_id=project_id,
                kind="create",
                message_template=DEFAULT_CREATE_TEMPLATE,
                notify_roles=["reporter", "followers"],
                enabled=False,
            )
        )

    await ensure_project_workflow_defs(db, project_id)
    await ensure_project_role_defs(db, project_id)
    await ensure_project_option_defs(db, project_id)
