from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import CasePriority, TestCase
from app.models.template import TemplateScene
from app.services.case_module_paths import load_project_modules
from app.services.case_module_resolve import ImportModuleResolver
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
    row_is_empty,
    sort_template_fields,
    validation_error_message,
)
from app.services.excel_import_common import (
    generate_template_workbook as _generate_template_workbook,
)
from app.services.field_validator import load_project_member_user_ids, validate_custom_fields
from app.services.links import set_case_requirements, validate_requirement_ids
from app.services.template_fields import RESERVED_FIELD_NAMES_BY_SCENE

CASE_SYSTEM_IMPORT_COLUMNS: list[tuple[str, Optional[str]]] = [
    ("模块", "module_path"),
    ("用例标题", "title"),
    ("优先级", "priority"),
    ("前置条件", "precondition"),
    ("步骤", "step_text"),
    ("预期结果", "expected_result"),
    ("关联需求", "requirement_ids"),
]

CASE_HEADER_ALIASES: dict[str, str] = {
    "标题": "用例标题",
    "用例名称": "用例标题",
    "名称": "用例标题",
    "所属模块": "模块",
    "模块路径": "模块",
    "步骤描述": "步骤",
    "步骤说明": "步骤",
    "预期": "预期结果",
    "需求": "关联需求",
    "关联需求编号": "关联需求",
}

CASE_RESERVED_FIELD_NAMES = RESERVED_FIELD_NAMES_BY_SCENE["functional_case"]
CASE_EXAMPLE_TITLE = "示例用例标题"

CaseImportError = ImportRowError
CaseImportResult = ImportResult


def _parse_priority(raw: str) -> tuple[Optional[CasePriority], Optional[str]]:
    if not raw:
        return CasePriority.P2, None
    upper = raw.upper()
    try:
        return CasePriority(upper), None
    except ValueError:
        return None, f"无效优先级「{raw}」，应为 P0/P1/P2/P3"


def build_case_import_columns(fields_schema: list) -> list[ImportColumn]:
    return build_import_columns(
        CASE_SYSTEM_IMPORT_COLUMNS,
        fields_schema,
        reserved_names=CASE_RESERVED_FIELD_NAMES,
    )


async def parse_import_workbook(
    content: bytes,
    *,
    project_id: str,
    user_id: str,
    db: AsyncSession,
) -> CaseImportResult:
    project_modules = await load_project_modules(db, project_id)
    module_resolver = ImportModuleResolver(
        modules=list(project_modules),
        project_id=project_id,
        db=db,
    )

    fields_schema = await load_fields_schema(db, project_id, TemplateScene.functional_case)
    columns = build_case_import_columns(fields_schema)
    expected = expected_headers(columns)
    rows = load_workbook_rows(content)
    data_start = resolve_header_and_data_start(
        rows, expected, columns, CASE_HEADER_ALIASES, example_title=CASE_EXAMPLE_TITLE
    )

    member_ids = await load_project_member_user_ids(db, project_id)
    by_email, by_name = await load_member_lookups(db, project_id)

    created = 0
    errors: list[CaseImportError] = []
    system_headers = {h for h, _ in CASE_SYSTEM_IMPORT_COLUMNS}

    for row_idx, row in enumerate(rows[data_start:], start=data_start + 1):
        cells = [cell_str(c) for c in row] + [""] * (len(columns) - len(row))
        cells = cells[: len(columns)]
        if row_is_empty(cells):
            continue

        title = ""
        module_path_raw = ""
        priority = CasePriority.P2
        precondition: Optional[str] = None
        step_text: Optional[str] = None
        expected_result: Optional[str] = None
        requirement_ids: list[str] = []
        custom_fields: dict[str, Any] = {}
        row_error: Optional[str] = None

        for col_index, (col, val) in enumerate(zip(columns, cells)):
            if row_error:
                break
            if col.kind == "system":
                if not col.system_key:
                    continue
                if col.system_key == "module_path":
                    module_path_raw = val
                elif col.system_key == "title":
                    title = val
                    if not title:
                        row_error = "用例标题不能为空"
                elif col.system_key == "priority":
                    p, err = _parse_priority(val)
                    if err:
                        row_error = err
                    elif p:
                        priority = p
                elif col.system_key == "precondition":
                    precondition = val or None
                elif col.system_key == "step_text":
                    step_text = val or None
                elif col.system_key == "expected_result":
                    expected_result = val or None
                elif col.system_key == "requirement_ids":
                    req_ids, err = await parse_requirement_ids_cell(db, project_id, val)
                    if err:
                        row_error = err
                    else:
                        requirement_ids = req_ids
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
            errors.append(CaseImportError(row=row_idx, message=row_error))
            continue
        if not title:
            errors.append(CaseImportError(row=row_idx, message="用例标题不能为空"))
            continue

        target_module_id, mod_err = await module_resolver.resolve(module_path_raw)
        if mod_err:
            errors.append(CaseImportError(row=row_idx, message=mod_err))
            continue
        if not target_module_id:
            errors.append(CaseImportError(row=row_idx, message="无法解析模块"))
            continue

        req_msg = check_required_custom_fields(
            fields_schema,
            custom_fields,
            system_headers=system_headers,
            reserved_names=CASE_RESERVED_FIELD_NAMES,
        )
        if req_msg:
            errors.append(CaseImportError(row=row_idx, message=req_msg))
            continue

        try:
            await validate_requirement_ids(db, project_id, requirement_ids)
        except ValueError as e:
            errors.append(CaseImportError(row=row_idx, message=str(e)))
            continue

        try:
            validated_custom = validate_custom_fields(
                fields_schema,
                custom_fields,
                project_id=project_id,
                project_member_ids=member_ids,
            )
        except HTTPException as exc:
            errors.append(CaseImportError(row=row_idx, message=validation_error_message(exc)))
            continue

        case = TestCase(
            project_id=project_id,
            module_id=target_module_id,
            title=title[:512],
            priority=priority,
            precondition=precondition,
            step_text=step_text,
            expected_result=expected_result,
            steps=[],
            tags=[],
            custom_fields=validated_custom,
            created_by=user_id,
        )
        db.add(case)
        await db.flush()
        await set_case_requirements(db, case.id, requirement_ids)
        created += 1

    return CaseImportResult(created=created, errors=errors)


async def generate_template_bytes(db: AsyncSession, project_id: str) -> bytes:
    fields_schema = await load_fields_schema(db, project_id, TemplateScene.functional_case)
    columns = build_case_import_columns(fields_schema)
    return _generate_template_workbook(columns, sheet_title="用例导入")
