from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import io

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import (
    ProjectContext,
    require_project_context,
    require_project_context_tester,
    user_can_full_edit_project,
)
from app.models.bug import (
    Bug,
    BugAttachment,
    BugCaseLink,
    BugComment,
    BugFollowerLink,
    BugStatusHistory,
)
from app.models.requirement import BugPlanLink, BugRequirementLink
from app.models.template import BugStatus, ProjectFieldTemplate, TemplateScene
from app.models.user import User
from app.schemas.user import UserOut
from app.schemas.bug import (
    BugActivityOut,
    BugAttachmentOut,
    BugCaseLinkOut,
    BugCommentCreate,
    BugCommentOut,
    BugCreate,
    BugFollowerScheduleUpdate,
    BugImportErrorOut,
    BugImportResultOut,
    BugListPageOut,
    BugOut,
    BugUpdate,
)
from app.services.bug_follower_schedule import (
    BugFollowerScheduleError,
    get_bug_follower_link_or_raise,
    update_bug_follower_schedule,
)
from app.services.bug_import import generate_bug_template_bytes, parse_bug_import_workbook
from app.services.bug_activity import list_bug_activities_merged, log_bug_activity
from app.services.bug_delete import delete_bug_cascade
from app.services.bug_filters import apply_bug_list_filters, parse_custom_filters
from app.services.bug_sort import bug_severity_rank_column
from app.services.list_filter_utils import parse_created_date_bounds
from app.services.field_validator import load_project_member_user_ids, validate_custom_fields
from app.services.file_cleanup import cleanup_after_bug_content_change, cleanup_after_bug_deleted
from app.services.file_refs import file_keys_from_bug
from app.services.links import (
    set_bug_followers,
    set_bug_plans,
    set_bug_requirements,
    validate_plan_ids,
    validate_project_member_ids,
    validate_requirement_ids,
)
from app.services.file_storage import build_file_download_url, delete_object_safe, upload_bytes
from app.services.project_setup import ensure_project_defaults
from app.services.versions import validate_version_id
from app.services.serializers import bug_out, bug_out_list_batch
from app.services.wecom_notify import notify_bug_created, notify_bug_status_change

router = APIRouter(prefix="/bugs", tags=["bugs"])

_DEFAULT_PAGE_SIZE = 20
_MAX_PAGE_SIZE = 100


def _bug_attachment_out(att: BugAttachment) -> BugAttachmentOut:
    return BugAttachmentOut(
        id=att.id,
        bug_id=att.bug_id,
        object_key=att.object_key,
        filename=att.filename,
        size=att.size,
        created_at=att.created_at,
        url=build_file_download_url(att.object_key),
    )


async def _next_bug_num(project_id: str, db: AsyncSession) -> int:
    result = await db.execute(select(func.max(Bug.num)).where(Bug.project_id == project_id))
    current = result.scalar() or 0
    return current + 1


async def _record_status_history(
    bug: Bug,
    from_key: str | None,
    to_key: str,
    user_id: str,
    db: AsyncSession,
    *,
    notified: bool,
) -> None:
    history = BugStatusHistory(
        bug_id=bug.id,
        from_status=from_key,
        to_status=to_key,
        changed_by=user_id,
        notified_at=datetime.now(timezone.utc).replace(tzinfo=None) if notified else None,
    )
    db.add(history)


@router.get("", response_model=BugListPageOut)
async def list_bugs(
    status_key: Optional[str] = Query(None, description="状态 key，逗号分隔多值 OR 匹配"),
    exclude_status_key: Optional[str] = Query(
        None, description="排除的状态 key，逗号分隔多值 NOT IN 匹配"
    ),
    assignee_id: Optional[str] = Query(None, description="经办人 ID，逗号分隔；含 __empty__ 表示未指定"),
    reporter_id: Optional[str] = Query(None, description="提出人 ID，逗号分隔多值 OR 匹配"),
    follower_id: Optional[str] = Query(None, description="跟进人 ID，逗号分隔；含 __empty__ 表示无跟进人"),
    plan_version_id: Optional[str] = Query(None, description="规划版本 ID，逗号分隔；含 __empty__ 表示未关联"),
    found_version_id: Optional[str] = Query(None, description="发现版本 ID，逗号分隔；含 __empty__ 表示未关联"),
    requirement_id: Optional[str] = Query(None, description="关联需求 ID，逗号分隔；含 __empty__ 表示未关联"),
    plan_id: Optional[str] = Query(None, description="关联计划 ID，逗号分隔；含 __empty__ 表示未关联"),
    q: Optional[str] = None,
    custom_filters: Optional[str] = Query(
        None, description="JSON: { fieldId: value | [values] | __empty__ }，同字段多值 OR"
    ),
    created_date: Optional[str] = Query(
        None, description="创建日期 YYYY-MM-DD，按 UTC+8 日历日筛选"
    ),
    sort_by: Optional[str] = Query(
        None, description="排序：severity=按严重程度（致命优先）"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(_DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE),
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    await ensure_project_defaults(ctx.project_id, db)
    tpl = await db.execute(
        select(ProjectFieldTemplate).where(
            ProjectFieldTemplate.project_id == ctx.project_id,
            ProjectFieldTemplate.scene == TemplateScene.bug,
        )
    )
    template_row = tpl.scalar_one_or_none()
    template_fields: list = template_row.fields if template_row else []

    parsed_custom: dict[str, list[str]] = {}
    if custom_filters:
        try:
            parsed_custom = parse_custom_filters(custom_filters)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if created_date:
        try:
            parse_created_date_bounds(created_date)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    stmt = select(Bug).where(Bug.project_id == ctx.project_id)
    stmt = apply_bug_list_filters(
        stmt,
        status_key=status_key,
        exclude_status_key=exclude_status_key,
        assignee_id=assignee_id,
        reporter_id=reporter_id,
        follower_id=follower_id,
        plan_version_id=plan_version_id,
        found_version_id=found_version_id,
        requirement_id=requirement_id,
        plan_id=plan_id,
        q=q,
        created_date=created_date,
        template_fields=template_fields,
        custom_filters=parsed_custom or None,
    )
    count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    if sort_by == "severity":
        order_by = (
            bug_severity_rank_column(Bug.custom_fields).asc(),
            Bug.num.desc(),
        )
    elif created_date:
        order_by = (Bug.created_at.desc(),)
    else:
        order_by = (Bug.num.desc(),)
    result = await db.execute(
        stmt.order_by(*order_by).offset(offset).limit(page_size)
    )
    bugs = list(result.scalars().all())
    items = await bug_out_list_batch(bugs, db)
    return BugListPageOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/import/template")
async def download_bug_import_template(
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    await ensure_project_defaults(ctx.project_id, db)
    content = await generate_bug_template_bytes(db, ctx.project_id)
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="bug_import_template.xlsx"'},
    )


@router.post("/import", response_model=BugImportResultOut)
async def import_bugs(
    file: UploadFile = File(...),
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    filename = (file.filename or "").lower()
    if not filename.endswith(".xlsx"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 .xlsx 文件")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件为空")
    await ensure_project_defaults(ctx.project_id, db)
    result = await parse_bug_import_workbook(
        content,
        project_id=ctx.project_id,
        user_id=ctx.user.id,
        db=db,
        record_status_history=_record_status_history,
    )
    return BugImportResultOut(
        created=result.created,
        errors=[BugImportErrorOut(row=e.row, message=e.message) for e in result.errors],
    )


@router.post("", response_model=BugOut, status_code=status.HTTP_201_CREATED)
async def create_bug(
    body: BugCreate,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    await ensure_project_defaults(ctx.project_id, db)
    status_key = body.status_key
    if not status_key:
        first = await db.execute(
            select(BugStatus).where(BugStatus.project_id == ctx.project_id).order_by(BugStatus.sort)
        )
        s = first.scalars().first()
        if not s:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No bug statuses configured")
        status_key = s.key
    reporter_id = body.reporter_id or ctx.user.id
    try:
        await validate_requirement_ids(db, ctx.project_id, body.requirement_ids)
        await validate_plan_ids(db, ctx.project_id, body.plan_ids)
        await validate_version_id(db, ctx.project_id, body.plan_version_id)
        await validate_version_id(db, ctx.project_id, body.found_version_id)
        await validate_project_member_ids(db, ctx.project_id, [reporter_id])
        await validate_project_member_ids(db, ctx.project_id, body.follower_ids)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    tpl = await db.execute(
        select(ProjectFieldTemplate).where(
            ProjectFieldTemplate.project_id == ctx.project_id,
            ProjectFieldTemplate.scene == TemplateScene.bug,
        )
    )
    member_ids = await load_project_member_user_ids(db, ctx.project_id)
    custom = validate_custom_fields(
        tpl.scalar_one().fields,
        body.custom_fields,
        project_id=ctx.project_id,
        project_member_ids=member_ids,
    )
    bug = Bug(
        project_id=ctx.project_id,
        num=await _next_bug_num(ctx.project_id, db),
        title=body.title,
        status_key=status_key,
        assignee_id=body.assignee_id,
        reporter_id=reporter_id,
        description=body.description,
        plan_version_id=body.plan_version_id,
        found_version_id=body.found_version_id,
        custom_fields=custom,
    )
    db.add(bug)
    await db.flush()
    await set_bug_requirements(db, bug.id, body.requirement_ids)
    await set_bug_plans(db, bug.id, body.plan_ids)
    await set_bug_followers(db, bug.id, body.follower_ids)
    for cid in body.case_ids:
        db.add(BugCaseLink(bug_id=bug.id, case_id=cid))
    await db.flush()
    await _record_status_history(bug, None, status_key, ctx.user.id, db, notified=False)
    mention_count = await notify_bug_created(db, bug)
    await log_bug_activity(
        db,
        bug_id=bug.id,
        actor_id=ctx.user.id,
        action_type="create",
        summary="创建了缺陷",
    )
    if mention_count is not None:
        summary = (
            f"已发送企微通知（@{mention_count} 人）"
            if mention_count > 0
            else "已发送企微通知（未 @ 任何人）"
        )
        await log_bug_activity(
            db,
            bug_id=bug.id,
            actor_id=ctx.user.id,
            action_type="wecom_notify",
            summary=summary,
        )
    await db.refresh(bug)
    return await bug_out(bug, db)


@router.get("/{bug_id}", response_model=BugOut)
async def get_bug(
    bug_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    bug = await db.get(Bug, bug_id)
    if not bug or bug.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bug not found")
    return await bug_out(bug, db)


@router.patch("/{bug_id}/follower-schedules/{user_id}", response_model=BugOut)
async def patch_bug_follower_schedule(
    bug_id: str,
    user_id: str,
    body: BugFollowerScheduleUpdate,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    bug = await db.get(Bug, bug_id)
    if not bug or bug.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bug not found")
    can_full_edit = await user_can_full_edit_project(ctx.user, ctx.project_id, db)
    if ctx.user.id != user_id and not can_full_edit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the follower or testers may update this schedule",
        )
    try:
        link = await get_bug_follower_link_or_raise(db, bug_id, user_id)
        data = body.model_dump(exclude_unset=True)
        await update_bug_follower_schedule(
            db,
            link,
            fix_estimate_points=data.get("fix_estimate_points"),
            clear_estimate="fix_estimate_points" in data and data["fix_estimate_points"] is None,
            scheduled_start=data.get("scheduled_start"),
            scheduled_end=data.get("scheduled_end"),
            clear_schedule=(
                "scheduled_start" in data
                and data["scheduled_start"] is None
                and "scheduled_end" in data
                and data["scheduled_end"] is None
            ),
            fields_set=set(data.keys()),
        )
    except BugFollowerScheduleError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    await log_bug_activity(
        db,
        bug_id=bug.id,
        actor_id=ctx.user.id,
        action_type="field_update",
        summary="更新了跟进排期",
        detail={"field": "follower_schedule", "user_id": user_id},
    )
    await db.refresh(bug)
    return await bug_out(bug, db)


@router.patch("/{bug_id}", response_model=BugOut)
async def update_bug(
    bug_id: str,
    body: BugUpdate,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    bug = await db.get(Bug, bug_id)
    if not bug or bug.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bug not found")
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    can_full_edit = await user_can_full_edit_project(ctx.user, ctx.project_id, db)
    if not can_full_edit:
        disallowed = set(data.keys()) - {"status_key"}
        if disallowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only testers may edit bug details; members may change status only",
            )
    old_status = bug.status_key
    old_file_keys = file_keys_from_bug(bug)
    old_title = bug.title
    old_plan_version_id = bug.plan_version_id
    old_found_version_id = bug.found_version_id
    req_ids = data.pop("requirement_ids", None)
    plan_ids = data.pop("plan_ids", None)
    follower_ids = data.pop("follower_ids", None)
    if "reporter_id" in data or follower_ids is not None:
        try:
            if "reporter_id" in data and data["reporter_id"]:
                await validate_project_member_ids(db, ctx.project_id, [data["reporter_id"]])
            if follower_ids is not None:
                await validate_project_member_ids(db, ctx.project_id, follower_ids)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if "plan_version_id" in data or "found_version_id" in data:
        try:
            if "plan_version_id" in data:
                await validate_version_id(db, ctx.project_id, data.get("plan_version_id"))
            if "found_version_id" in data:
                await validate_version_id(db, ctx.project_id, data.get("found_version_id"))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if req_ids is not None:
        try:
            await validate_requirement_ids(db, ctx.project_id, req_ids)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if plan_ids is not None:
        try:
            await validate_plan_ids(db, ctx.project_id, plan_ids)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if "custom_fields" in data:
        tpl = await db.execute(
            select(ProjectFieldTemplate).where(
                ProjectFieldTemplate.project_id == ctx.project_id,
                ProjectFieldTemplate.scene == TemplateScene.bug,
            )
        )
        member_ids = await load_project_member_user_ids(db, ctx.project_id)
        data["custom_fields"] = validate_custom_fields(
            tpl.scalar_one().fields,
            data["custom_fields"],
            project_id=ctx.project_id,
            project_member_ids=member_ids,
        )
    for k, v in data.items():
        setattr(bug, k, v)
    await db.flush()
    if req_ids is not None:
        await set_bug_requirements(db, bug.id, req_ids)
        await log_bug_activity(
            db,
            bug_id=bug.id,
            actor_id=ctx.user.id,
            action_type="link_change",
            summary="更新了关联需求",
        )
    if plan_ids is not None:
        await set_bug_plans(db, bug.id, plan_ids)
        await log_bug_activity(
            db,
            bug_id=bug.id,
            actor_id=ctx.user.id,
            action_type="link_change",
            summary="更新了关联测试计划",
        )
    if follower_ids is not None:
        await set_bug_followers(db, bug.id, follower_ids)
        await log_bug_activity(
            db,
            bug_id=bug.id,
            actor_id=ctx.user.id,
            action_type="field_update",
            summary="更新了跟进人",
            detail={"field": "followers"},
        )
    if "reporter_id" in data:
        await log_bug_activity(
            db,
            bug_id=bug.id,
            actor_id=ctx.user.id,
            action_type="field_update",
            summary="修改了提出人",
            detail={"field": "reporter_id"},
        )
    if "title" in data and data["title"] != old_title:
        await log_bug_activity(
            db,
            bug_id=bug.id,
            actor_id=ctx.user.id,
            action_type="field_update",
            summary="修改了标题",
            detail={"field": "title"},
        )
    if "description" in data:
        await log_bug_activity(
            db,
            bug_id=bug.id,
            actor_id=ctx.user.id,
            action_type="field_update",
            summary="修改了描述",
            detail={"field": "description"},
        )
    if "plan_version_id" in data and data["plan_version_id"] != old_plan_version_id:
        await log_bug_activity(
            db,
            bug_id=bug.id,
            actor_id=ctx.user.id,
            action_type="field_update",
            summary="修改了规划迭代",
            detail={"field": "plan_version_id"},
        )
    if "found_version_id" in data and data["found_version_id"] != old_found_version_id:
        await log_bug_activity(
            db,
            bug_id=bug.id,
            actor_id=ctx.user.id,
            action_type="field_update",
            summary="修改了发现版本",
            detail={"field": "found_version_id"},
        )
    if "description" in data or "custom_fields" in data:
        await cleanup_after_bug_content_change(
            db, ctx.project_id, bug, old_file_keys, file_keys_from_bug(bug)
        )
    if "status_key" in data and data["status_key"] != old_status:
        mention_count = await notify_bug_status_change(db, bug, old_status, data["status_key"])
        await _record_status_history(
            bug, old_status, data["status_key"], ctx.user.id, db, notified=mention_count is not None
        )
        if mention_count is not None:
            summary = (
                f"已发送企微通知（@{mention_count} 人）"
                if mention_count > 0
                else "已发送企微通知（未 @ 任何人）"
            )
            await log_bug_activity(
                db,
                bug_id=bug.id,
                actor_id=ctx.user.id,
                action_type="wecom_notify",
                summary=summary,
            )
    await db.refresh(bug)
    return await bug_out(bug, db)


@router.delete("/{bug_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bug(
    bug_id: str,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    bug = await db.get(Bug, bug_id)
    if not bug or bug.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bug not found")
    await cleanup_after_bug_deleted(db, ctx.project_id, bug)
    await delete_bug_cascade(db, bug)


@router.get("/{bug_id}/comments", response_model=list[BugCommentOut])
async def list_comments(
    bug_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    bug = await db.get(Bug, bug_id)
    if not bug or bug.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bug not found")
    result = await db.execute(
        select(BugComment).where(BugComment.bug_id == bug_id).order_by(BugComment.created_at.asc())
    )
    comments = list(result.scalars().all())
    user_ids = {c.user_id for c in comments}
    user_map: dict[str, User] = {}
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        user_map = {u.id: u for u in users_result.scalars().all()}
    out: list[BugCommentOut] = []
    for c in comments:
        user = user_map.get(c.user_id)
        out.append(
            BugCommentOut(
                id=c.id,
                bug_id=c.bug_id,
                user_id=c.user_id,
                body=c.body,
                created_at=c.created_at,
                user=UserOut.model_validate(user) if user else None,
            )
        )
    return out


@router.post("/{bug_id}/comments", response_model=BugCommentOut, status_code=status.HTTP_201_CREATED)
async def create_comment(
    bug_id: str,
    body: BugCommentCreate,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    bug = await db.get(Bug, bug_id)
    if not bug or bug.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bug not found")
    comment = BugComment(bug_id=bug_id, user_id=ctx.user.id, body=body.body.strip())
    db.add(comment)
    await db.flush()
    await log_bug_activity(
        db,
        bug_id=bug_id,
        actor_id=ctx.user.id,
        action_type="comment",
        summary="发表了评论",
        detail={"comment_id": comment.id},
    )
    await db.refresh(comment)
    user = await db.get(User, ctx.user.id)
    return BugCommentOut(
        id=comment.id,
        bug_id=comment.bug_id,
        user_id=comment.user_id,
        body=comment.body,
        created_at=comment.created_at,
        user=UserOut.model_validate(user) if user else None,
    )


@router.get("/{bug_id}/activities", response_model=list[BugActivityOut])
async def list_activities(
    bug_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    bug = await db.get(Bug, bug_id)
    if not bug or bug.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bug not found")
    items = await list_bug_activities_merged(db, bug_id, project_id=bug.project_id)
    return [BugActivityOut.model_validate(i) for i in items]


@router.get("/{bug_id}/cases", response_model=list[BugCaseLinkOut])
async def list_bug_cases(
    bug_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    bug = await db.get(Bug, bug_id)
    if not bug or bug.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bug not found")
    result = await db.execute(select(BugCaseLink).where(BugCaseLink.bug_id == bug_id))
    return [BugCaseLinkOut.model_validate(l) for l in result.scalars().all()]


@router.post("/{bug_id}/cases/{case_id}", response_model=BugCaseLinkOut, status_code=status.HTTP_201_CREATED)
async def link_case(
    bug_id: str,
    case_id: str,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    bug = await db.get(Bug, bug_id)
    if not bug or bug.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bug not found")
    existing = await db.execute(
        select(BugCaseLink).where(BugCaseLink.bug_id == bug_id, BugCaseLink.case_id == case_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already linked")
    link = BugCaseLink(bug_id=bug_id, case_id=case_id)
    db.add(link)
    await db.flush()
    return BugCaseLinkOut.model_validate(link)


@router.delete("/{bug_id}/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_case(
    bug_id: str,
    case_id: str,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BugCaseLink).where(BugCaseLink.bug_id == bug_id, BugCaseLink.case_id == case_id)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    await db.delete(link)


@router.get("/{bug_id}/attachments", response_model=list[BugAttachmentOut])
async def list_attachments(
    bug_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    bug = await db.get(Bug, bug_id)
    if not bug or bug.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bug not found")
    result = await db.execute(select(BugAttachment).where(BugAttachment.bug_id == bug_id))
    return [_bug_attachment_out(a) for a in result.scalars().all()]


@router.post("/{bug_id}/attachments", response_model=BugAttachmentOut, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    bug_id: str,
    file: UploadFile = File(...),
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    bug = await db.get(Bug, bug_id)
    if not bug or bug.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bug not found")
    data = await file.read()
    object_key, size = await upload_bytes(
        db, data, file.filename or "file.bin", file.content_type or "application/octet-stream"
    )
    att = BugAttachment(bug_id=bug_id, object_key=object_key, filename=file.filename or "file", size=size)
    db.add(att)
    await db.flush()
    await log_bug_activity(
        db,
        bug_id=bug_id,
        actor_id=ctx.user.id,
        action_type="attachment",
        summary=f"上传了附件：{att.filename}",
        detail={"attachment_id": att.id},
    )
    await db.refresh(att)
    return _bug_attachment_out(att)


@router.delete("/{bug_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    bug_id: str,
    attachment_id: str,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    bug = await db.get(Bug, bug_id)
    if not bug or bug.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bug not found")
    att = await db.get(BugAttachment, attachment_id)
    if not att or att.bug_id != bug_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    filename = att.filename
    object_key = att.object_key
    await log_bug_activity(
        db,
        bug_id=bug_id,
        actor_id=ctx.user.id,
        action_type="attachment",
        summary=f"删除了附件：{filename}",
        detail={"attachment_id": attachment_id},
    )
    await db.delete(att)
    await db.flush()
    await delete_object_safe(db, object_key)
