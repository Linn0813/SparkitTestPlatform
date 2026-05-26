from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import ProjectContext, require_project_context, require_project_context_catalog
from app.models.requirement import Requirement, RequirementActivity, RequirementComment, RequirementStatus
from app.models.template import ProjectFieldTemplate, TemplateScene
from app.models.user import User
from app.schemas.requirement import (
    RequirementActivityOut,
    RequirementCommentCreate,
    RequirementCommentOut,
    RequirementCreate,
    RequirementNodeActionBody,
    RequirementNodeTaskCreate,
    RequirementNodeTaskOut,
    RequirementNodeTaskUpdate,
    RequirementOut,
    RequirementUpdate,
    RequirementWorkflowEnabledUpdate,
    RequirementWorkflowOut,
)
from app.schemas.user import UserOut
from app.services.requirement_activity import log_requirement_activity
from app.services.requirement_nodes import (
    RequirementNodeError,
    apply_node_action,
    close_requirement,
    load_node_map,
    reopen_from_closed,
    sync_requirement_status_from_workflow,
    update_requirement_enabled_nodes,
)
from app.services.requirement_serializers import (
    build_node_task_outs,
    build_requirement_workflow_out,
    requirement_out,
    validate_requirement_role_user_ids,
)
from app.services.requirement_node_tasks import (
    RequirementNodeTaskError,
    create_node_task,
    delete_node_task,
    fill_empty_task_assignees_from_requirement,
    get_task_or_raise,
    load_tasks_for_requirement,
    update_node_task,
)
from app.services.field_validator import load_project_member_user_ids, validate_custom_fields
from app.services.project_setup import ensure_project_defaults
from app.services.requirement_config import validate_requirement_option
from app.services.requirement_workflow import ensure_project_workflow_defs, init_requirement_progress_from_defs, load_project_workflow_defs

from app.services.requirement_filters import apply_requirement_list_filters
from app.services.versions import validate_version_id

router = APIRouter(prefix="/requirements", tags=["requirements"])


async def _get_requirement_or_404(
    requirement_id: str, project_id: str, db: AsyncSession
) -> Requirement:
    row = await db.get(Requirement, requirement_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")
    return row


async def _next_req_num(project_id: str, db: AsyncSession) -> int:
    result = await db.execute(select(func.max(Requirement.num)).where(Requirement.project_id == project_id))
    return (result.scalar() or 0) + 1


def _role_ids_from_body(data: dict) -> list[str | None]:
    ids: list[str | None] = []
    keys = (
        "frontend_rd_id",
        "backend_rd_id",
        "pm_id",
        "tech_owner_id",
        "qa_id",
        "designer_id",
    )
    ids.extend(data.get(k) for k in keys if k in data)
    assignees = data.get("role_assignee_ids")
    if isinstance(assignees, dict):
        for role_ids in assignees.values():
            if isinstance(role_ids, list):
                ids.extend(uid for uid in role_ids if uid)
    return ids


def _sync_role_id_fields_from_assignees(data: dict) -> None:
    from app.services.requirement_serializers import ROLE_KEY_TO_ID_FIELD

    assignees = data.get("role_assignee_ids")
    if not isinstance(assignees, dict):
        return
    for role_key, field in ROLE_KEY_TO_ID_FIELD.items():
        role_ids = assignees.get(role_key) or []
        data[field] = role_ids[0] if role_ids else None


async def _load_requirement_template_fields(db: AsyncSession, project_id: str) -> list:
    await ensure_project_defaults(project_id, db)
    result = await db.execute(
        select(ProjectFieldTemplate).where(
            ProjectFieldTemplate.project_id == project_id,
            ProjectFieldTemplate.scene == TemplateScene.requirement,
        )
    )
    tpl = result.scalar_one_or_none()
    return tpl.fields if tpl and tpl.fields else []


async def _validate_requirement_fields(db: AsyncSession, project_id: str, data: dict) -> None:
    if "priority" in data and data["priority"] is not None:
        await validate_requirement_option(db, project_id, "priority", data["priority"])
    if "req_type" in data and data["req_type"] is not None:
        await validate_requirement_option(db, project_id, "req_type", data["req_type"])
    if "custom_fields" in data and data["custom_fields"] is not None:
        fields_schema = await _load_requirement_template_fields(db, project_id)
        member_ids = await load_project_member_user_ids(db, project_id)
        data["custom_fields"] = validate_custom_fields(
            fields_schema,
            data["custom_fields"],
            project_id=project_id,
            project_member_ids=member_ids,
        )


@router.get("", response_model=list[RequirementOut])
async def list_requirements(
    q: Optional[str] = None,
    version_id: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    req_type: Optional[str] = None,
    frontend_rd_id: Optional[str] = None,
    backend_rd_id: Optional[str] = None,
    pm_id: Optional[str] = None,
    qa_id: Optional[str] = None,
    developer_id: Optional[str] = None,
    dev_handoff_from: Optional[date] = None,
    dev_handoff_to: Optional[date] = None,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Requirement).where(Requirement.project_id == ctx.project_id)
    stmt = apply_requirement_list_filters(
        stmt,
        q=q,
        version_id=version_id,
        status=status,
        priority=priority,
        req_type=req_type,
        frontend_rd_id=frontend_rd_id,
        backend_rd_id=backend_rd_id,
        pm_id=pm_id,
        qa_id=qa_id,
        developer_id=developer_id,
        dev_handoff_from=dev_handoff_from,
        dev_handoff_to=dev_handoff_to,
    )
    result = await db.execute(stmt.order_by(Requirement.num.desc()))
    rows = result.scalars().all()
    return [await requirement_out(r, db) for r in rows]


@router.post("", response_model=RequirementOut, status_code=status.HTTP_201_CREATED)
async def create_requirement(
    body: RequirementCreate,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    try:
        create_data = body.model_dump()
        _sync_role_id_fields_from_assignees(create_data)
        await validate_version_id(db, ctx.project_id, body.version_id)
        await validate_requirement_option(db, ctx.project_id, "priority", body.priority)
        await validate_requirement_option(db, ctx.project_id, "req_type", body.req_type)
        await validate_requirement_role_user_ids(
            db,
            ctx.project_id,
            _role_ids_from_body(create_data),
        )
        await _validate_requirement_fields(db, ctx.project_id, create_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    defs = await ensure_project_workflow_defs(db, ctx.project_id)
    enabled_map = create_data.get("enabled")
    assignees = create_data.get("role_assignee_ids")
    row = Requirement(
        project_id=ctx.project_id,
        num=await _next_req_num(ctx.project_id, db),
        title=create_data["title"],
        external_url=create_data.get("external_url"),
        version_id=create_data.get("version_id"),
        priority=create_data["priority"],
        req_type=create_data["req_type"],
        custom_fields=create_data.get("custom_fields") or {},
        status=RequirementStatus.draft,
        frontend_rd_id=create_data.get("frontend_rd_id"),
        backend_rd_id=create_data.get("backend_rd_id"),
        pm_id=create_data.get("pm_id"),
        tech_owner_id=create_data.get("tech_owner_id"),
        qa_id=create_data.get("qa_id"),
        designer_id=create_data.get("designer_id"),
        role_assignee_ids=assignees if isinstance(assignees, dict) else {},
        created_by=ctx.user.id,
    )
    db.add(row)
    await db.flush()
    await init_requirement_progress_from_defs(db, row, defs, enabled_map=enabled_map)
    from app.services.requirement_workflow import init_requirement_tasks_from_defs

    await init_requirement_tasks_from_defs(db, row, defs, enabled_map=enabled_map)

    from app.services.requirement_nodes import load_node_map, reconcile_workflow_nodes
    from app.services.requirement_status_rules import load_status_rules_for_derive

    nodes = await load_node_map(db, row.id)
    rules = await load_status_rules_for_derive(db, ctx.project_id)
    reconcile_workflow_nodes(row, nodes, defs, rules=rules, actor_id=ctx.user.id)
    await db.flush()
    await log_requirement_activity(
        db,
        requirement_id=row.id,
        actor_id=ctx.user.id,
        action_type="create",
        summary="创建了需求",
    )
    await db.refresh(row)
    return await requirement_out(row, db)


@router.get("/{requirement_id}", response_model=RequirementOut)
async def get_requirement(
    requirement_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_requirement_or_404(requirement_id, ctx.project_id, db)
    await fill_empty_task_assignees_from_requirement(db, row)
    from app.services.requirement_nodes import ensure_requirement_nodes_auto_started

    await ensure_requirement_nodes_auto_started(db, row, actor_id=ctx.user.id)
    return await requirement_out(row, db)


@router.get("/{requirement_id}/workflow", response_model=RequirementWorkflowOut)
async def get_requirement_workflow(
    requirement_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_requirement_or_404(requirement_id, ctx.project_id, db)
    return await build_requirement_workflow_out(row, db)


@router.put("/{requirement_id}/workflow", response_model=RequirementWorkflowOut)
async def update_requirement_workflow(
    requirement_id: str,
    body: RequirementWorkflowEnabledUpdate,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_requirement_or_404(requirement_id, ctx.project_id, db)
    defs = await load_project_workflow_defs(db, ctx.project_id)
    nodes = await load_node_map(db, row.id)
    try:
        await update_requirement_enabled_nodes(
            db, row, nodes, defs, body.enabled, actor_id=ctx.user.id
        )
    except RequirementNodeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    await db.refresh(row)
    return await build_requirement_workflow_out(row, db)


@router.patch("/{requirement_id}", response_model=RequirementOut)
async def update_requirement(
    requirement_id: str,
    body: RequirementUpdate,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_requirement_or_404(requirement_id, ctx.project_id, db)
    data = body.model_dump(exclude_unset=True)
    _sync_role_id_fields_from_assignees(data)
    try:
        if "version_id" in data:
            await validate_version_id(db, ctx.project_id, data.get("version_id"))
        if _role_ids_from_body(data):
            await validate_requirement_role_user_ids(db, ctx.project_id, _role_ids_from_body(data))
        await _validate_requirement_fields(db, ctx.project_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    for k, v in data.items():
        setattr(row, k, v)
    await db.flush()
    role_id_fields = (
        "frontend_rd_id",
        "backend_rd_id",
        "pm_id",
        "tech_owner_id",
        "qa_id",
        "designer_id",
    )
    if "role_assignee_ids" in data or any(k in data for k in role_id_fields):
        await fill_empty_task_assignees_from_requirement(db, row)
    await db.refresh(row)
    return await requirement_out(row, db)


@router.delete("/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_requirement(
    requirement_id: str,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import delete

    from app.models.requirement import RequirementActivity, RequirementComment, RequirementNodeProgress, RequirementNodeTask

    row = await _get_requirement_or_404(requirement_id, ctx.project_id, db)
    await db.execute(delete(RequirementComment).where(RequirementComment.requirement_id == row.id))
    await db.execute(delete(RequirementActivity).where(RequirementActivity.requirement_id == row.id))
    await db.execute(delete(RequirementNodeTask).where(RequirementNodeTask.requirement_id == row.id))
    await db.execute(delete(RequirementNodeProgress).where(RequirementNodeProgress.requirement_id == row.id))
    await db.delete(row)


@router.post("/{requirement_id}/nodes/{node_key}", response_model=RequirementOut)
async def requirement_node_action(
    requirement_id: str,
    node_key: str,
    body: RequirementNodeActionBody,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_requirement_or_404(requirement_id, ctx.project_id, db)
    defs = await load_project_workflow_defs(db, ctx.project_id)
    nodes = await load_node_map(db, row.id)
    try:
        await apply_node_action(
            db,
            row,
            nodes,
            defs,
            node_key=node_key,
            action=body.action,
            actor_id=ctx.user.id,
        )
    except RequirementNodeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    from app.services.requirement_nodes import ensure_requirement_nodes_auto_started

    await ensure_requirement_nodes_auto_started(db, row, actor_id=ctx.user.id)
    await db.refresh(row)
    return await requirement_out(row, db)


@router.get("/{requirement_id}/node-tasks", response_model=list[RequirementNodeTaskOut])
async def list_requirement_node_tasks(
    requirement_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_requirement_or_404(requirement_id, ctx.project_id, db)
    tasks = await load_tasks_for_requirement(db, row.id)
    return await build_node_task_outs(tasks, db)


@router.post(
    "/{requirement_id}/nodes/{node_key}/tasks",
    response_model=RequirementOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_requirement_node_task(
    requirement_id: str,
    node_key: str,
    body: RequirementNodeTaskCreate,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_requirement_or_404(requirement_id, ctx.project_id, db)
    try:
        if body.assignee_id:
            await validate_requirement_role_user_ids(db, ctx.project_id, [body.assignee_id])
        await create_node_task(
            db,
            row,
            node_key,
            title=body.title,
            role_key=body.role_key,
            assignee_id=body.assignee_id,
            estimate_points=body.estimate_points,
            scheduled_start=body.scheduled_start,
            scheduled_end=body.scheduled_end,
        )
    except RequirementNodeTaskError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    await db.refresh(row)
    return await requirement_out(row, db)


@router.patch(
    "/{requirement_id}/nodes/{node_key}/tasks/{task_id}",
    response_model=RequirementOut,
)
async def update_requirement_node_task(
    requirement_id: str,
    node_key: str,
    task_id: str,
    body: RequirementNodeTaskUpdate,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_requirement_or_404(requirement_id, ctx.project_id, db)
    try:
        task = await get_task_or_raise(db, row.id, node_key, task_id)
        data = body.model_dump(exclude_unset=True)
        if data.get("assignee_id"):
            await validate_requirement_role_user_ids(db, ctx.project_id, [data["assignee_id"]])
        await update_node_task(
            db,
            row,
            task,
            title=data.get("title"),
            role_key=data.get("role_key"),
            assignee_id=data.get("assignee_id"),
            clear_assignee="assignee_id" in data and data["assignee_id"] is None,
            estimate_points=data.get("estimate_points"),
            clear_estimate="estimate_points" in data and data["estimate_points"] is None,
            scheduled_start=data.get("scheduled_start"),
            scheduled_end=data.get("scheduled_end"),
            clear_schedule=(
                "scheduled_start" in data
                and data["scheduled_start"] is None
                and "scheduled_end" in data
                and data["scheduled_end"] is None
            ),
            sort=data.get("sort"),
            fields_set=set(data.keys()),
        )
    except RequirementNodeTaskError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    await db.refresh(row)
    return await requirement_out(row, db)


@router.delete(
    "/{requirement_id}/nodes/{node_key}/tasks/{task_id}",
    response_model=RequirementOut,
)
async def delete_requirement_node_task(
    requirement_id: str,
    node_key: str,
    task_id: str,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_requirement_or_404(requirement_id, ctx.project_id, db)
    try:
        task = await get_task_or_raise(db, row.id, node_key, task_id)
        await delete_node_task(db, row, task)
    except RequirementNodeTaskError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    await db.refresh(row)
    return await requirement_out(row, db)


@router.post("/{requirement_id}/close", response_model=RequirementOut)
async def requirement_close(
    requirement_id: str,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_requirement_or_404(requirement_id, ctx.project_id, db)
    try:
        await close_requirement(db, row, actor_id=ctx.user.id)
    except RequirementNodeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    await db.refresh(row)
    return await requirement_out(row, db)


@router.post("/{requirement_id}/reopen-closed", response_model=RequirementOut)
async def requirement_reopen_closed(
    requirement_id: str,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_requirement_or_404(requirement_id, ctx.project_id, db)
    defs = await load_project_workflow_defs(db, ctx.project_id)
    nodes = await load_node_map(db, row.id)
    try:
        await reopen_from_closed(db, row, nodes, defs, actor_id=ctx.user.id)
    except RequirementNodeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    await db.refresh(row)
    return await requirement_out(row, db)


@router.post("/{requirement_id}/sync-status", response_model=RequirementOut)
async def requirement_sync_status(
    requirement_id: str,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_requirement_or_404(requirement_id, ctx.project_id, db)
    await sync_requirement_status_from_workflow(db, row, actor_id=ctx.user.id)
    await db.refresh(row)
    return await requirement_out(row, db)


@router.get("/{requirement_id}/activities", response_model=list[RequirementActivityOut])
async def list_requirement_activities(
    requirement_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    await _get_requirement_or_404(requirement_id, ctx.project_id, db)
    result = await db.execute(
        select(RequirementActivity)
        .where(RequirementActivity.requirement_id == requirement_id)
        .order_by(RequirementActivity.created_at.desc())
    )
    items = []
    for a in result.scalars().all():
        actor = await db.get(User, a.actor_id)
        items.append(
            RequirementActivityOut(
                id=a.id,
                action_type=a.action_type,
                summary=a.summary,
                detail=a.detail,
                actor=UserOut.model_validate(actor) if actor else None,
                created_at=a.created_at,
            )
        )
    return items


@router.get("/{requirement_id}/comments", response_model=list[RequirementCommentOut])
async def list_requirement_comments(
    requirement_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    await _get_requirement_or_404(requirement_id, ctx.project_id, db)
    result = await db.execute(
        select(RequirementComment)
        .where(RequirementComment.requirement_id == requirement_id)
        .order_by(RequirementComment.created_at.asc())
    )
    comments = list(result.scalars().all())
    user_ids = {c.user_id for c in comments}
    user_map: dict[str, User] = {}
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        user_map = {u.id: u for u in users_result.scalars().all()}
    out: list[RequirementCommentOut] = []
    for c in comments:
        user = user_map.get(c.user_id)
        out.append(
            RequirementCommentOut(
                id=c.id,
                requirement_id=c.requirement_id,
                user_id=c.user_id,
                body=c.body,
                created_at=c.created_at,
                user=UserOut.model_validate(user) if user else None,
            )
        )
    return out


@router.post("/{requirement_id}/comments", response_model=RequirementCommentOut, status_code=status.HTTP_201_CREATED)
async def create_requirement_comment(
    requirement_id: str,
    body: RequirementCommentCreate,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    await _get_requirement_or_404(requirement_id, ctx.project_id, db)
    comment = RequirementComment(
        requirement_id=requirement_id,
        user_id=ctx.user.id,
        body=body.body.strip(),
    )
    db.add(comment)
    await db.flush()
    await log_requirement_activity(
        db,
        requirement_id=requirement_id,
        actor_id=ctx.user.id,
        action_type="comment",
        summary="发表了评论",
        detail={"comment_id": comment.id},
    )
    await db.refresh(comment)
    user = await db.get(User, ctx.user.id)
    return RequirementCommentOut(
        id=comment.id,
        requirement_id=comment.requirement_id,
        user_id=comment.user_id,
        body=comment.body,
        created_at=comment.created_at,
        user=UserOut.model_validate(user) if user else None,
    )
