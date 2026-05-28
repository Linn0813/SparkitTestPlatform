from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.version_nodes import VERSION_WECOM_EVENT_KEYS
from app.core.database import get_db
from app.core.deps import ProjectContext, require_project_context, require_project_context_admin
from app.models.template import ProjectIntegration
from app.models.version_workflow import VersionWecomNotifyRule
from app.schemas.version_wecom import (
    VersionWecomIntegrationOut,
    VersionWecomIntegrationUpdate,
    VersionWecomNotifyRuleOut,
    VersionWecomNotifyRuleUpdate,
    VersionWecomTestRequest,
)
from app.services.version_wecom_defaults import WECOM_EVENT_LABELS
from app.services.version_wecom_rules import ensure_project_version_wecom_rules
from app.services.wecom import send_wecom_text

router = APIRouter(prefix="/projects", tags=["version-wecom"])


async def _get_integration(project_id: str, db: AsyncSession) -> ProjectIntegration:
    result = await db.execute(
        select(ProjectIntegration).where(ProjectIntegration.project_id == project_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        row = ProjectIntegration(project_id=project_id)
        db.add(row)
        await db.flush()
    return row


def _rule_out(rule: VersionWecomNotifyRule) -> VersionWecomNotifyRuleOut:
    return VersionWecomNotifyRuleOut(
        id=rule.id,
        project_id=rule.project_id,
        event_key=rule.event_key,
        event_label=WECOM_EVENT_LABELS.get(rule.event_key, rule.event_key),
        message_template=rule.message_template,
        notify_user_ids=list(rule.notify_user_ids or []),
        enabled=rule.enabled,
    )


@router.get("/{project_id}/integrations/version-wecom", response_model=VersionWecomIntegrationOut)
async def get_version_wecom(
    project_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    row = await _get_integration(project_id, db)
    return VersionWecomIntegrationOut(
        project_id=project_id,
        version_wecom_webhook_url=row.version_wecom_webhook_url,
        version_wecom_enabled=row.version_wecom_enabled,
        app_public_url=row.app_public_url,
    )


@router.patch("/{project_id}/integrations/version-wecom", response_model=VersionWecomIntegrationOut)
async def update_version_wecom(
    project_id: str,
    body: VersionWecomIntegrationUpdate,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    row = await _get_integration(project_id, db)
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    await db.flush()
    return VersionWecomIntegrationOut(
        project_id=project_id,
        version_wecom_webhook_url=row.version_wecom_webhook_url,
        version_wecom_enabled=row.version_wecom_enabled,
        app_public_url=row.app_public_url,
    )


@router.post("/{project_id}/integrations/version-wecom/test")
async def test_version_wecom(
    project_id: str,
    body: VersionWecomTestRequest,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    row = await _get_integration(project_id, db)
    if not row.version_wecom_webhook_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook URL not configured")
    ok = await send_wecom_text(row.version_wecom_webhook_url, body.message)
    if not ok:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="WeCom send failed")
    return {"ok": True}


@router.get("/{project_id}/version-wecom-notify-rules", response_model=list[VersionWecomNotifyRuleOut])
async def list_version_wecom_rules(
    project_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    await ensure_project_version_wecom_rules(project_id, db)
    result = await db.execute(
        select(VersionWecomNotifyRule)
        .where(VersionWecomNotifyRule.project_id == project_id)
        .order_by(VersionWecomNotifyRule.event_key)
    )
    return [_rule_out(r) for r in result.scalars().all()]


@router.put(
    "/{project_id}/version-wecom-notify-rules/{event_key}",
    response_model=VersionWecomNotifyRuleOut,
)
async def upsert_version_wecom_rule(
    project_id: str,
    event_key: str,
    body: VersionWecomNotifyRuleUpdate,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    if event_key not in VERSION_WECOM_EVENT_KEYS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown event key")
    await ensure_project_version_wecom_rules(project_id, db)
    result = await db.execute(
        select(VersionWecomNotifyRule).where(
            VersionWecomNotifyRule.project_id == project_id,
            VersionWecomNotifyRule.event_key == event_key,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    data = body.model_dump(exclude_unset=True)
    if "notify_user_ids" in data and data["notify_user_ids"] is not None:
        row.notify_user_ids = data["notify_user_ids"]
    if "message_template" in data:
        row.message_template = data["message_template"]
    if "enabled" in data and data["enabled"] is not None:
        row.enabled = data["enabled"]
    await db.flush()
    return _rule_out(row)
