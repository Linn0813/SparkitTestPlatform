from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import ProjectContext, require_project_context, require_project_context_admin
from app.models.template import ProjectIntegration
from app.models.version_workflow import VersionWecomNotifyRule
from app.schemas.version_wecom import (
    VersionWecomIntegrationOut,
    VersionWecomIntegrationUpdate,
    VersionWecomNotifyRuleCreate,
    VersionWecomNotifyRuleOptionOut,
    VersionWecomNotifyRuleOut,
    VersionWecomNotifyRuleUpdate,
    VersionWecomTestRequest,
)
from app.services.version_wecom_rules import (
    VersionWecomRuleError,
    list_version_wecom_rule_options,
    load_project_notifyable_nodes,
    node_label_for_rule,
    validate_rule_node_key,
)
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


async def _rule_out(db: AsyncSession, rule: VersionWecomNotifyRule) -> VersionWecomNotifyRuleOut:
    node_label = await node_label_for_rule(db, rule.project_id, rule.node_key)
    return VersionWecomNotifyRuleOut(
        id=rule.id,
        project_id=rule.project_id,
        node_key=rule.node_key,
        node_label=node_label,
        message_template=rule.message_template,
        notify_user_ids=list(rule.notify_user_ids or []),
        enabled=rule.enabled,
    )


def _apply_rule_update(row: VersionWecomNotifyRule, body: VersionWecomNotifyRuleUpdate) -> None:
    data = body.model_dump(exclude_unset=True)
    if "notify_user_ids" in data and data["notify_user_ids"] is not None:
        row.notify_user_ids = data["notify_user_ids"]
    if "message_template" in data:
        template = (data["message_template"] or "").strip()
        if not template:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="消息模板不能为空")
        row.message_template = template
    if "enabled" in data and data["enabled"] is not None:
        row.enabled = data["enabled"]


async def _get_rule_or_404(
    db: AsyncSession,
    project_id: str,
    rule_id: str,
) -> VersionWecomNotifyRule:
    row = await db.get(VersionWecomNotifyRule, rule_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return row


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


@router.get(
    "/{project_id}/version-wecom-notify-rule-options",
    response_model=list[VersionWecomNotifyRuleOptionOut],
)
async def list_version_wecom_rule_options_endpoint(
    project_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    options = await list_version_wecom_rule_options(project_id, db)
    return [VersionWecomNotifyRuleOptionOut.model_validate(o) for o in options]


@router.get("/{project_id}/version-wecom-notify-rules", response_model=list[VersionWecomNotifyRuleOut])
async def list_version_wecom_rules(
    project_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    result = await db.execute(
        select(VersionWecomNotifyRule)
        .where(VersionWecomNotifyRule.project_id == project_id)
        .order_by(VersionWecomNotifyRule.node_key)
    )
    rules = list(result.scalars().all())
    return [await _rule_out(db, r) for r in rules]


@router.post(
    "/{project_id}/version-wecom-notify-rules",
    response_model=VersionWecomNotifyRuleOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_version_wecom_rule(
    project_id: str,
    body: VersionWecomNotifyRuleCreate,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    node_key = body.node_key.strip()
    if not node_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择工作流节点")
    try:
        await validate_rule_node_key(db, project_id, node_key)
    except VersionWecomRuleError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    template = body.message_template.strip()
    if not template:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="消息模板不能为空")

    existing = await db.execute(
        select(VersionWecomNotifyRule.id).where(
            VersionWecomNotifyRule.project_id == project_id,
            VersionWecomNotifyRule.node_key == node_key,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该节点已存在通知规则")

    row = VersionWecomNotifyRule(
        project_id=project_id,
        node_key=node_key,
        message_template=template,
        notify_user_ids=list(body.notify_user_ids or []),
        enabled=body.enabled,
    )
    db.add(row)
    try:
        await db.flush()
    except IntegrityError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该节点已存在通知规则") from e
    return await _rule_out(db, row)


@router.patch(
    "/{project_id}/version-wecom-notify-rules/{rule_id}",
    response_model=VersionWecomNotifyRuleOut,
)
async def patch_version_wecom_rule(
    project_id: str,
    rule_id: str,
    body: VersionWecomNotifyRuleUpdate,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    row = await _get_rule_or_404(db, project_id, rule_id)
    _apply_rule_update(row, body)
    await db.flush()
    return await _rule_out(db, row)


@router.delete(
    "/{project_id}/version-wecom-notify-rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_version_wecom_rule(
    project_id: str,
    rule_id: str,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    row = await _get_rule_or_404(db, project_id, rule_id)
    await db.delete(row)
    await db.flush()


@router.put(
    "/{project_id}/version-wecom-notify-rules/by-node/{node_key}",
    response_model=VersionWecomNotifyRuleOut,
)
async def update_version_wecom_rule_by_node(
    project_id: str,
    node_key: str,
    body: VersionWecomNotifyRuleUpdate,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    result = await db.execute(
        select(VersionWecomNotifyRule).where(
            VersionWecomNotifyRule.project_id == project_id,
            VersionWecomNotifyRule.node_key == node_key,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    _apply_rule_update(row, body)
    await db.flush()
    return await _rule_out(db, row)
