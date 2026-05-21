from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import ProjectContext, require_project_context, require_project_context_admin
from app.models.bug import Bug
from app.models.template import BugStatus, ProjectFieldTemplate, ProjectIntegration, TemplateScene
from app.schemas.template import (
    BugStatusCreate,
    BugStatusOut,
    BugStatusUpdate,
    FieldTemplateOut,
    FieldTemplateUpdate,
    WecomIntegrationOut,
    WecomIntegrationUpdate,
    WecomTestRequest,
)
from app.services.project_setup import ensure_project_defaults
from app.services.template_fields import validate_template_fields
from app.services.wecom import send_wecom_markdown

router = APIRouter(prefix="/projects", tags=["templates"])


@router.get("/{project_id}/templates/{scene}", response_model=FieldTemplateOut)
async def get_template(
    project_id: str,
    scene: TemplateScene,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    await ensure_project_defaults(project_id, db)
    result = await db.execute(
        select(ProjectFieldTemplate).where(
            ProjectFieldTemplate.project_id == project_id,
            ProjectFieldTemplate.scene == scene,
        )
    )
    tpl = result.scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return FieldTemplateOut(project_id=project_id, scene=scene.value, fields=tpl.fields)


@router.patch("/{project_id}/templates/{scene}", response_model=FieldTemplateOut)
async def update_template(
    project_id: str,
    scene: TemplateScene,
    body: FieldTemplateUpdate,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    await ensure_project_defaults(project_id, db)
    result = await db.execute(
        select(ProjectFieldTemplate).where(
            ProjectFieldTemplate.project_id == project_id,
            ProjectFieldTemplate.scene == scene,
        )
    )
    tpl = result.scalar_one()
    tpl.fields = validate_template_fields(body.fields, scene=scene.value)
    await db.flush()
    return FieldTemplateOut(project_id=project_id, scene=scene.value, fields=tpl.fields)


@router.get("/{project_id}/bug-statuses", response_model=list[BugStatusOut])
async def list_bug_statuses(
    project_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    await ensure_project_defaults(project_id, db)
    result = await db.execute(
        select(BugStatus).where(BugStatus.project_id == project_id).order_by(BugStatus.sort)
    )
    return [BugStatusOut.model_validate(s) for s in result.scalars().all()]


@router.post("/{project_id}/bug-statuses", response_model=BugStatusOut, status_code=status.HTTP_201_CREATED)
async def create_bug_status(
    project_id: str,
    body: BugStatusCreate,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    existing = await db.execute(
        select(BugStatus).where(BugStatus.project_id == project_id, BugStatus.key == body.key)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status key exists")
    row = BugStatus(project_id=project_id, **body.model_dump())
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return BugStatusOut.model_validate(row)


@router.patch("/{project_id}/bug-statuses/{status_id}", response_model=BugStatusOut)
async def update_bug_status(
    project_id: str,
    status_id: str,
    body: BugStatusUpdate,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    row = await db.get(BugStatus, status_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await db.flush()
    await db.refresh(row)
    return BugStatusOut.model_validate(row)


@router.delete("/{project_id}/bug-statuses/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bug_status(
    project_id: str,
    status_id: str,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    row = await db.get(BugStatus, status_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status not found")
    count_q = await db.execute(
        select(func.count()).select_from(Bug).where(
            Bug.project_id == project_id, Bug.status_key == row.key
        )
    )
    in_use = count_q.scalar() or 0
    if in_use > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Status is used by {in_use} bug(s); reassign bugs first",
        )
    await db.delete(row)


@router.get("/{project_id}/integrations/wecom", response_model=WecomIntegrationOut)
async def get_wecom(
    project_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    await ensure_project_defaults(project_id, db)
    result = await db.execute(
        select(ProjectIntegration).where(ProjectIntegration.project_id == project_id)
    )
    row = result.scalar_one()
    return WecomIntegrationOut(
        project_id=project_id,
        wecom_webhook_url=row.wecom_webhook_url,
        wecom_enabled=row.wecom_enabled,
        status_notify_template=row.status_notify_template,
        create_notify_template=row.create_notify_template,
        notify_on_create=row.notify_on_create,
    )


@router.patch("/{project_id}/integrations/wecom", response_model=WecomIntegrationOut)
async def update_wecom(
    project_id: str,
    body: WecomIntegrationUpdate,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    await ensure_project_defaults(project_id, db)
    result = await db.execute(
        select(ProjectIntegration).where(ProjectIntegration.project_id == project_id)
    )
    row = result.scalar_one()
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await db.flush()
    return WecomIntegrationOut(
        project_id=project_id,
        wecom_webhook_url=row.wecom_webhook_url,
        wecom_enabled=row.wecom_enabled,
        status_notify_template=row.status_notify_template,
        create_notify_template=row.create_notify_template,
        notify_on_create=row.notify_on_create,
    )


@router.post("/{project_id}/integrations/wecom/test")
async def test_wecom(
    project_id: str,
    body: WecomTestRequest,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    result = await db.execute(
        select(ProjectIntegration).where(ProjectIntegration.project_id == project_id)
    )
    row = result.scalar_one_or_none()
    if not row or not row.wecom_webhook_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook URL not configured")
    ok = await send_wecom_markdown(row.wecom_webhook_url, f"### 测试消息\n{body.message}")
    if not ok:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="WeCom send failed")
    return {"message": "ok"}
