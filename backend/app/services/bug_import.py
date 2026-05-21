from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bug import Bug
from app.models.plan import TestPlan
from app.models.project_version import ProjectVersion
from app.models.template import BugStatus, TemplateScene
from app.services.bug_activity import log_bug_activity
from app.services.excel_import_common import (
    ImportColumn,
    ImportResult,
    ImportRowError,
    build_import_columns,
    cell_str,
    check_required_custom_fields,
    expected_headers,
    load_fields_schema,
    load_member_lookups,
    load_workbook_rows,
    parse_custom_cell,
    parse_requirement_ids_cell,
    resolve_header_and_data_start,
    resolve_member,
    row_is_empty,
    TAG_SPLIT,
    validation_error_message,
)
from app.services.excel_import_common import (
    generate_template_workbook as _generate_template_workbook,
)
from app.services.field_validator import load_project_member_user_ids, validate_custom_fields
from app.services.links import (
    set_bug_followers,
    set_bug_plans,
    set_bug_requirements,
    validate_plan_ids,
    validate_project_member_ids,
    validate_requirement_ids,
)
from app.services.template_fields import RESERVED_FIELD_NAMES_BY_SCENE
from app.services.versions import validate_version_id
BUG_SYSTEM_IMPORT_COLUMNS: list[tuple[str, Optional[str]]] = [
    ("缺陷标题", "title"),
    ("状态", "status_key"),
    ("提出人", "reporter_id"),
    ("跟进人", "follower_ids"),
    ("描述", "description"),
    ("关联需求", "requirement_ids"),
    ("关联测试计划", "plan_ids"),
    ("规划迭代", "plan_version_id"),
    ("发现版本", "found_version_id"),
]

BUG_HEADER_ALIASES: dict[str, str] = {
    "标题": "缺陷标题",
    "缺陷名称": "缺陷标题",
    "名称": "缺陷标题",
    "需求": "关联需求",
    "关联需求编号": "关联需求",
    "测试计划": "关联测试计划",
    "关联计划": "关联测试计划",
    "规划版本": "规划迭代",
    "发现迭代": "发现版本",
}

BUG_RESERVED_FIELD_NAMES = RESERVED_FIELD_NAMES_BY_SCENE["bug"]

BugImportError = ImportRowError
BugImportResult = ImportResult


async def _next_bug_num(project_id: str, db: AsyncSession) -> int:
    result = await db.execute(select(func.max(Bug.num)).where(Bug.project_id == project_id))
    current = result.scalar() or 0
    return current + 1


async def _default_status_key(project_id: str, db: AsyncSession) -> str | None:
    result = await db.execute(
        select(BugStatus).where(BugStatus.project_id == project_id).order_by(BugStatus.sort)
    )
    s = result.scalars().first()
    return s.key if s else None


class _BugImportLookups:
    def __init__(self) -> None:
        self.status_by_label: dict[str, str] = {}
        self.status_by_key: dict[str, str] = {}
        self.plan_by_name: dict[str, str | None] = {}
        self.version_by_name: dict[str, str | None] = {}

    @classmethod
    async def load(cls, db: AsyncSession, project_id: str) -> _BugImportLookups:
        obj = cls()
        statuses = await db.execute(select(BugStatus).where(BugStatus.project_id == project_id))
        for s in statuses.scalars().all():
            obj.status_by_key[s.key] = s.key
            label = s.label.strip()
            if label:
                if label in obj.status_by_label:
                    obj.status_by_label[label] = ""
                else:
                    obj.status_by_label[label] = s.key

        plans = await db.execute(select(TestPlan).where(TestPlan.project_id == project_id))
        for p in plans.scalars().all():
            name = p.name.strip()
            if not name:
                continue
            if name in obj.plan_by_name:
                obj.plan_by_name[name] = None
            else:
                obj.plan_by_name[name] = p.id

        versions = await db.execute(
            select(ProjectVersion).where(ProjectVersion.project_id == project_id)
        )
        for v in versions.scalars().all():
            name = v.name.strip()
            if not name:
                continue
            if name in obj.version_by_name:
                obj.version_by_name[name] = None
            else:
                obj.version_by_name[name] = v.id
        return obj

    def resolve_status(self, raw: str, default_key: str | None) -> tuple[str | None, Optional[str]]:
        if not raw.strip():
            return default_key, None if default_key else "项目未配置缺陷状态"
        token = raw.strip()
        if token in self.status_by_key:
            return token, None
        key = self.status_by_label.get(token)
        if key == "":
            return None, f"状态「{token}」不唯一，请填写状态 key"
        if key:
            return key, None
        return None, f"未找到状态「{token}」"

    def resolve_plan_ids(self, raw: str) -> tuple[list[str], Optional[str]]:
        if not raw.strip():
            return [], None
        ids: list[str] = []
        for part in [p.strip() for p in TAG_SPLIT.split(raw) if p.strip()]:
            pid = self.plan_by_name.get(part)
            if pid is None and part in self.plan_by_name:
                return [], f"测试计划「{part}」不唯一"
            if not pid:
                return [], f"未找到测试计划「{part}」"
            ids.append(pid)
        return ids, None

    def resolve_version_id(self, raw: str, field_label: str) -> tuple[str | None, Optional[str]]:
        if not raw.strip():
            return None, None
        token = raw.strip()
        vid = self.version_by_name.get(token)
        if vid is None and token in self.version_by_name:
            return None, f"{field_label}「{token}」不唯一"
        if not vid:
            return None, f"未找到{field_label}「{token}」"
        return vid, None


def build_bug_import_columns(fields_schema: list) -> list[ImportColumn]:
    return build_import_columns(
        BUG_SYSTEM_IMPORT_COLUMNS,
        fields_schema,
        reserved_names=BUG_RESERVED_FIELD_NAMES,
    )


async def parse_bug_import_workbook(
    content: bytes,
    *,
    project_id: str,
    user_id: str,
    db: AsyncSession,
    record_status_history: Callable[..., Awaitable[None]],
) -> BugImportResult:
    default_status = await _default_status_key(project_id, db)
    if not default_status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No bug statuses configured")

    lookups = await _BugImportLookups.load(db, project_id)
    fields_schema = await load_fields_schema(db, project_id, TemplateScene.bug)
    columns = build_bug_import_columns(fields_schema)
    expected = expected_headers(columns)
    rows = load_workbook_rows(content)
    data_start = resolve_header_and_data_start(rows, expected, columns, BUG_HEADER_ALIASES)

    member_ids = await load_project_member_user_ids(db, project_id)
    by_email, by_name = await load_member_lookups(db, project_id)

    created = 0
    errors: list[BugImportError] = []
    system_headers = {h for h, _ in BUG_SYSTEM_IMPORT_COLUMNS}

    for row_idx, row in enumerate(rows[data_start:], start=data_start + 1):
        cells = [cell_str(c) for c in row] + [""] * (len(columns) - len(row))
        cells = cells[: len(columns)]
        if row_is_empty(cells):
            continue

        title = ""
        status_key: str | None = default_status
        reporter_id = user_id
        follower_ids: list[str] = []
        description: Optional[str] = None
        requirement_ids: list[str] = []
        plan_ids: list[str] = []
        plan_version_id: Optional[str] = None
        found_version_id: Optional[str] = None
        custom_fields: dict[str, Any] = {}
        row_error: Optional[str] = None

        for col_index, (col, val) in enumerate(zip(columns, cells)):
            if row_error:
                break
            if col.kind == "system":
                if not col.system_key:
                    continue
                if col.system_key == "title":
                    title = val
                    if not title:
                        row_error = "缺陷标题不能为空"
                elif col.system_key == "status_key":
                    sk, err = lookups.resolve_status(val, default_status)
                    if err:
                        row_error = err
                    elif sk:
                        status_key = sk
                elif col.system_key == "reporter_id":
                    if val.strip():
                        uid, err = resolve_member(val, by_email, by_name)
                        if err:
                            row_error = err
                        elif uid:
                            reporter_id = uid
                elif col.system_key == "follower_ids":
                    if val.strip():
                        parsed, err = parse_custom_cell(
                            {"type": "member_multi", "name": "跟进人", "id": "__followers"},
                            val,
                            None,
                            by_email=by_email,
                            by_name=by_name,
                        )
                        if err:
                            row_error = err
                        elif isinstance(parsed, list):
                            follower_ids = parsed
                elif col.system_key == "description":
                    description = val or None
                elif col.system_key == "requirement_ids":
                    req_ids, err = await parse_requirement_ids_cell(db, project_id, val)
                    if err:
                        row_error = err
                    else:
                        requirement_ids = req_ids
                elif col.system_key == "plan_ids":
                    pids, err = lookups.resolve_plan_ids(val)
                    if err:
                        row_error = err
                    else:
                        plan_ids = pids
                elif col.system_key == "plan_version_id":
                    vid, err = lookups.resolve_version_id(val, "规划迭代")
                    if err:
                        row_error = err
                    else:
                        plan_version_id = vid
                elif col.system_key == "found_version_id":
                    vid, err = lookups.resolve_version_id(val, "发现版本")
                    if err:
                        row_error = err
                    else:
                        found_version_id = vid
            elif col.field:
                original = row[col_index] if col_index < len(row) else None
                parsed, err = parse_custom_cell(
                    col.field, val, original, by_email=by_email, by_name=by_name
                )
                if err:
                    row_error = err
                elif parsed is not None:
                    custom_fields[col.field["id"]] = parsed

        if row_error:
            errors.append(BugImportError(row=row_idx, message=row_error))
            continue
        if not title:
            errors.append(BugImportError(row=row_idx, message="缺陷标题不能为空"))
            continue
        if not status_key:
            errors.append(BugImportError(row=row_idx, message="无法确定缺陷状态"))
            continue

        req_msg = check_required_custom_fields(
            fields_schema,
            custom_fields,
            system_headers=system_headers,
            reserved_names=BUG_RESERVED_FIELD_NAMES,
        )
        if req_msg:
            errors.append(BugImportError(row=row_idx, message=req_msg))
            continue

        try:
            await validate_requirement_ids(db, project_id, requirement_ids)
            await validate_plan_ids(db, project_id, plan_ids)
            await validate_version_id(db, project_id, plan_version_id)
            await validate_version_id(db, project_id, found_version_id)
            await validate_project_member_ids(db, project_id, [reporter_id])
            await validate_project_member_ids(db, project_id, follower_ids)
        except ValueError as e:
            errors.append(BugImportError(row=row_idx, message=str(e)))
            continue

        try:
            validated_custom = validate_custom_fields(
                fields_schema,
                custom_fields,
                project_id=project_id,
                project_member_ids=member_ids,
            )
        except HTTPException as exc:
            errors.append(BugImportError(row=row_idx, message=validation_error_message(exc)))
            continue

        bug = Bug(
            project_id=project_id,
            num=await _next_bug_num(project_id, db),
            title=title[:512],
            status_key=status_key,
            assignee_id=None,
            reporter_id=reporter_id,
            description=description,
            plan_version_id=plan_version_id,
            found_version_id=found_version_id,
            custom_fields=validated_custom,
        )
        db.add(bug)
        await db.flush()
        await set_bug_requirements(db, bug.id, requirement_ids)
        await set_bug_plans(db, bug.id, plan_ids)
        await set_bug_followers(db, bug.id, follower_ids)
        await record_status_history(bug, None, status_key, user_id, db, notified=False)
        # 批量导入不逐条发企微，避免外部请求拖慢导致前端超时、库内却已写入
        await log_bug_activity(
            db,
            bug_id=bug.id,
            actor_id=user_id,
            action_type="create",
            summary="通过导入创建了缺陷",
        )
        created += 1

    return BugImportResult(created=created, errors=errors)


async def generate_bug_template_bytes(db: AsyncSession, project_id: str) -> bytes:
    fields_schema = await load_fields_schema(db, project_id, TemplateScene.bug)
    columns = build_bug_import_columns(fields_schema)
    return _generate_template_workbook(columns, sheet_title="缺陷导入")
