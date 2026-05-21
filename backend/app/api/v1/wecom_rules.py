from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import ProjectContext, require_project_context, require_project_context_admin
from app.models.template import BugStatus
from app.models.wecom_rule import BugWecomNotifyRule
from app.schemas.wecom_rule import (
    WecomCreateRuleUpsert,
    WecomNotifyRuleCreate,
    WecomNotifyRuleOut,
    WecomNotifyRuleUpdate,
)
from app.services.wecom_notify import DEFAULT_CREATE_TEMPLATE

router = APIRouter(prefix="/projects", tags=["wecom-rules"])


async def _status_labels(db: AsyncSession, project_id: str) -> dict[str, str]:
    result = await db.execute(select(BugStatus).where(BugStatus.project_id == project_id))
    return {s.key: s.label for s in result.scalars().all()}


def _rule_out(rule: BugWecomNotifyRule, labels: dict[str, str]) -> WecomNotifyRuleOut:
    return WecomNotifyRuleOut(
        id=rule.id,
        project_id=rule.project_id,
        kind=rule.kind,
        from_status_key=rule.from_status_key,
        to_status_key=rule.to_status_key,
        message_template=rule.message_template,
        notify_roles=rule.notify_roles if isinstance(rule.notify_roles, list) else [],
        enabled=rule.enabled,
        created_at=rule.created_at,
        from_status_label=labels.get(rule.from_status_key) if rule.from_status_key else None,
        to_status_label=labels.get(rule.to_status_key) if rule.to_status_key else None,
    )


@router.get("/{project_id}/wecom-notify-rules", response_model=list[WecomNotifyRuleOut])
async def list_wecom_notify_rules(
    project_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    labels = await _status_labels(db, project_id)
    result = await db.execute(
        select(BugWecomNotifyRule)
        .where(BugWecomNotifyRule.project_id == project_id)
        .order_by(BugWecomNotifyRule.kind, BugWecomNotifyRule.from_status_key, BugWecomNotifyRule.to_status_key)
    )
    return [_rule_out(r, labels) for r in result.scalars().all()]


@router.post(
    "/{project_id}/wecom-notify-rules",
    response_model=WecomNotifyRuleOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_wecom_notify_rule(
    project_id: str,
    body: WecomNotifyRuleCreate,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    if body.kind == "transition":
        if not body.from_status_key or not body.to_status_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="from_status_key and to_status_key required for transition rules",
            )
        if body.from_status_key == body.to_status_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="from and to status must differ",
            )
    elif body.kind == "create":
        existing = await db.execute(
            select(BugWecomNotifyRule).where(
                BugWecomNotifyRule.project_id == project_id,
                BugWecomNotifyRule.kind == "create",
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Create rule already exists; use PUT /wecom-notify-rules/create",
            )

    row = BugWecomNotifyRule(
        project_id=project_id,
        kind=body.kind,
        from_status_key=body.from_status_key if body.kind == "transition" else None,
        to_status_key=body.to_status_key if body.kind == "transition" else None,
        message_template=body.message_template.strip(),
        notify_roles=body.notify_roles,
        enabled=body.enabled,
    )
    db.add(row)
    try:
        await db.flush()
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rule already exists for this transition",
        ) from e
    labels = await _status_labels(db, project_id)
    return _rule_out(row, labels)


@router.patch("/{project_id}/wecom-notify-rules/{rule_id}", response_model=WecomNotifyRuleOut)
async def update_wecom_notify_rule(
    project_id: str,
    rule_id: str,
    body: WecomNotifyRuleUpdate,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    row = await db.get(BugWecomNotifyRule, rule_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    data = body.model_dump(exclude_unset=True)
    if row.kind == "transition":
        from_k = data.get("from_status_key", row.from_status_key)
        to_k = data.get("to_status_key", row.to_status_key)
        if from_k and to_k and from_k == to_k:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="from and to status must differ",
            )
    for k, v in data.items():
        if k == "message_template" and v is not None:
            setattr(row, k, v.strip())
        else:
            setattr(row, k, v)
    try:
        await db.flush()
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rule already exists for this transition",
        ) from e
    labels = await _status_labels(db, project_id)
    return _rule_out(row, labels)


@router.delete("/{project_id}/wecom-notify-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wecom_notify_rule(
    project_id: str,
    rule_id: str,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    row = await db.get(BugWecomNotifyRule, rule_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    if row.kind == "create":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete create rule; disable it or update via PUT /wecom-notify-rules/create",
        )
    await db.delete(row)


@router.put("/{project_id}/wecom-notify-rules/create", response_model=WecomNotifyRuleOut)
async def upsert_create_rule(
    project_id: str,
    body: WecomCreateRuleUpsert,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    result = await db.execute(
        select(BugWecomNotifyRule).where(
            BugWecomNotifyRule.project_id == project_id,
            BugWecomNotifyRule.kind == "create",
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        tpl = body.message_template or DEFAULT_CREATE_TEMPLATE
        row = BugWecomNotifyRule(
            project_id=project_id,
            kind="create",
            message_template=tpl.strip(),
            notify_roles=body.notify_roles or ["reporter", "followers"],
            enabled=body.enabled if body.enabled is not None else True,
        )
        db.add(row)
    else:
        data = body.model_dump(exclude_unset=True)
        for k, v in data.items():
            if k == "message_template" and v is not None:
                row.message_template = v.strip()
            elif v is not None:
                setattr(row, k, v)
    await db.flush()
    labels = await _status_labels(db, project_id)
    return _rule_out(row, labels)
