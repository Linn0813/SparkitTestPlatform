from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import ProjectContext, require_project_context, require_project_context_admin
from app.models.template import BugStatus
from app.models.wecom_rule import BugWecomNotifyRule
from app.schemas.wecom_rule import (
    WecomCommentRuleUpsert,
    WecomCreateRuleUpsert,
    WecomNotifyRuleCreate,
    WecomNotifyRuleOut,
    WecomNotifyRuleUpdate,
)
from app.services.wecom_notify import (
    DEFAULT_BUG_COMMENT_TEMPLATE,
    DEFAULT_CREATE_TEMPLATE,
    DEFAULT_REQUIREMENT_COMMENT_TEMPLATE,
)
from app.services.wecom_rule_utils import (
    keys_signature,
    resolve_transition_keys_from_body,
    rule_transition_keys,
)

router = APIRouter(prefix="/projects", tags=["wecom-rules"])

_DEFAULT_COMMENT_ROLES: dict[str, list[str]] = {
    "bug": ["reporter", "followers", "assignee"],
    "requirement": ["creator", "role_assignees", "task_assignees"],
}


async def _status_labels(db: AsyncSession, project_id: str) -> dict[str, str]:
    result = await db.execute(select(BugStatus).where(BugStatus.project_id == project_id))
    return {s.key: s.label for s in result.scalars().all()}


def _labels_join(keys: list[str], labels: dict[str, str]) -> str | None:
    if not keys:
        return None
    return "、".join(labels.get(k, k) for k in keys)


def _rule_entity_type(rule: BugWecomNotifyRule) -> str:
    return getattr(rule, "entity_type", None) or "bug"


def _rule_out(rule: BugWecomNotifyRule, labels: dict[str, str]) -> WecomNotifyRuleOut:
    from_keys, to_keys = rule_transition_keys(rule)
    return WecomNotifyRuleOut(
        id=rule.id,
        project_id=rule.project_id,
        entity_type=_rule_entity_type(rule),
        kind=rule.kind,
        from_status_key=from_keys[0] if len(from_keys) == 1 else None,
        to_status_key=to_keys[0] if len(to_keys) == 1 else None,
        from_status_keys=from_keys,
        to_status_keys=to_keys,
        message_template=rule.message_template,
        notify_roles=rule.notify_roles if isinstance(rule.notify_roles, list) else [],
        enabled=rule.enabled,
        created_at=rule.created_at,
        from_status_label=_labels_join(from_keys, labels),
        to_status_label=_labels_join(to_keys, labels),
    )


async def _ensure_unique_transition_rule(
    db: AsyncSession,
    project_id: str,
    from_keys: list[str],
    to_keys: list[str],
    *,
    exclude_id: str | None = None,
) -> None:
    sig = keys_signature(from_keys, to_keys)
    result = await db.execute(
        select(BugWecomNotifyRule).where(
            BugWecomNotifyRule.project_id == project_id,
            BugWecomNotifyRule.entity_type == "bug",
            BugWecomNotifyRule.kind == "transition",
        )
    )
    for existing in result.scalars().all():
        if exclude_id and existing.id == exclude_id:
            continue
        ef, et = rule_transition_keys(existing)
        if keys_signature(ef, et) == sig:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rule already exists for this transition set",
            )


async def _ensure_unique_singleton_rule(
    db: AsyncSession,
    project_id: str,
    *,
    entity_type: str,
    kind: str,
) -> None:
    existing = await db.execute(
        select(BugWecomNotifyRule).where(
            BugWecomNotifyRule.project_id == project_id,
            BugWecomNotifyRule.entity_type == entity_type,
            BugWecomNotifyRule.kind == kind,
        )
    )
    if existing.scalar_one_or_none():
        endpoint = "create" if kind == "create" else "comment"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{kind} rule already exists; use PUT /wecom-notify-rules/{endpoint}",
        )


def _apply_transition_keys(row: BugWecomNotifyRule, from_keys: list[str], to_keys: list[str]) -> None:
    row.from_status_keys = from_keys
    row.to_status_keys = to_keys
    row.from_status_key = None
    row.to_status_key = None


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
        .order_by(BugWecomNotifyRule.entity_type, BugWecomNotifyRule.kind, BugWecomNotifyRule.created_at)
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
    entity_type = body.entity_type
    if body.kind in ("create", "transition") and entity_type != "bug":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="create and transition rules are only supported for bugs",
        )
    from_keys: list[str] = []
    to_keys: list[str] = []
    if body.kind == "transition":
        try:
            from_keys, to_keys = resolve_transition_keys_from_body(
                from_status_keys=body.from_status_keys,
                to_status_keys=body.to_status_keys,
                from_status_key=body.from_status_key,
                to_status_key=body.to_status_key,
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        await _ensure_unique_transition_rule(db, project_id, from_keys, to_keys)
    elif body.kind in ("create", "comment"):
        await _ensure_unique_singleton_rule(
            db, project_id, entity_type=entity_type, kind=body.kind
        )

    row = BugWecomNotifyRule(
        project_id=project_id,
        entity_type=entity_type,
        kind=body.kind,
        message_template=body.message_template.strip(),
        notify_roles=body.notify_roles,
        enabled=body.enabled,
    )
    if body.kind == "transition":
        _apply_transition_keys(row, from_keys, to_keys)
    db.add(row)
    await db.flush()
    labels = await _status_labels(db, project_id)
    await db.refresh(row)
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
    if row.kind in ("create", "comment"):
        data.pop("from_status_key", None)
        data.pop("to_status_key", None)
        data.pop("from_status_keys", None)
        data.pop("to_status_keys", None)
    elif row.kind == "transition":
        current_from, current_to = rule_transition_keys(row)
        try:
            from_keys, to_keys = resolve_transition_keys_from_body(
                from_status_keys=data.get("from_status_keys", current_from),
                to_status_keys=data.get("to_status_keys", current_to),
                from_status_key=data.get("from_status_key"),
                to_status_key=data.get("to_status_key"),
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        await _ensure_unique_transition_rule(db, project_id, from_keys, to_keys, exclude_id=rule_id)
        _apply_transition_keys(row, from_keys, to_keys)
        data.pop("from_status_key", None)
        data.pop("to_status_key", None)
        data.pop("from_status_keys", None)
        data.pop("to_status_keys", None)
    for k, v in data.items():
        if k == "message_template" and v is not None:
            setattr(row, k, v.strip())
        elif k == "enabled":
            row.enabled = v
        elif v is not None:
            setattr(row, k, v)
    await db.flush()
    labels = await _status_labels(db, project_id)
    await db.refresh(row)
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
            BugWecomNotifyRule.entity_type == "bug",
            BugWecomNotifyRule.kind == "create",
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        tpl = body.message_template or DEFAULT_CREATE_TEMPLATE
        row = BugWecomNotifyRule(
            project_id=project_id,
            entity_type="bug",
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
            elif k == "enabled":
                row.enabled = v
            elif v is not None:
                setattr(row, k, v)
    await db.flush()
    labels = await _status_labels(db, project_id)
    await db.refresh(row)
    return _rule_out(row, labels)


@router.put("/{project_id}/wecom-notify-rules/comment", response_model=WecomNotifyRuleOut)
async def upsert_comment_rule(
    project_id: str,
    body: WecomCommentRuleUpsert,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    entity_type = body.entity_type
    default_tpl = (
        DEFAULT_BUG_COMMENT_TEMPLATE
        if entity_type == "bug"
        else DEFAULT_REQUIREMENT_COMMENT_TEMPLATE
    )
    result = await db.execute(
        select(BugWecomNotifyRule).where(
            BugWecomNotifyRule.project_id == project_id,
            BugWecomNotifyRule.entity_type == entity_type,
            BugWecomNotifyRule.kind == "comment",
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        row = BugWecomNotifyRule(
            project_id=project_id,
            entity_type=entity_type,
            kind="comment",
            message_template=(body.message_template or default_tpl).strip(),
            notify_roles=body.notify_roles or _DEFAULT_COMMENT_ROLES[entity_type],
            enabled=body.enabled if body.enabled is not None else False,
        )
        db.add(row)
    else:
        data = body.model_dump(exclude_unset=True)
        data.pop("entity_type", None)
        for k, v in data.items():
            if k == "message_template" and v is not None:
                row.message_template = v.strip()
            elif k == "enabled":
                row.enabled = v
            elif v is not None:
                setattr(row, k, v)
    await db.flush()
    labels = await _status_labels(db, project_id)
    await db.refresh(row)
    return _rule_out(row, labels)
