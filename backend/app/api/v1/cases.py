from __future__ import annotations

import io
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import (
    ProjectContext,
    require_project_context,
    require_project_context_catalog,
    require_project_context_tester,
)
from app.models.case import CaseModule, TestCase
from app.models.requirement import CaseRequirementLink, Requirement
from app.models.template import ProjectFieldTemplate, TemplateScene
from app.schemas.case import (
    CaseImportErrorOut,
    CaseImportResultOut,
    CaseModuleCreate,
    CaseModuleOut,
    CaseModuleUpdate,
    TestCaseCreate,
    TestCaseOut,
    TestCaseUpdate,
)
from app.services.case_import import generate_template_bytes, parse_import_workbook
from app.services.field_validator import load_project_member_user_ids, validate_custom_fields
from app.services.file_cleanup import cleanup_after_case_content_change, cleanup_after_case_deleted
from app.services.file_refs import file_keys_from_case
from app.services.links import (
    set_case_requirements,
    validate_requirement_ids,
)
from app.services.case_filters import apply_case_list_filters
from app.services.custom_field_filters import parse_custom_filters
from app.services.project_setup import ensure_project_defaults
from app.services.serializers import case_out

router = APIRouter(prefix="/cases", tags=["cases"])


def _collect_module_descendant_ids(modules: list[CaseModule], root_id: str) -> set[str]:
    by_parent: dict[str | None, list[CaseModule]] = {}
    for m in modules:
        pid = m.parent_id
        by_parent.setdefault(pid, []).append(m)
    ids: set[str] = set()

    def walk(parent_id: str) -> None:
        for m in by_parent.get(parent_id, []):
            ids.add(m.id)
            walk(m.id)

    walk(root_id)
    return ids


def _build_module_path_map(modules: list[CaseModule]) -> dict[str, str]:
    by_id = {m.id: m for m in modules}

    def path_for(module_id: str) -> str:
        parts: list[str] = []
        cur: str | None = module_id
        seen: set[str] = set()
        while cur and cur not in seen:
            seen.add(cur)
            mod = by_id.get(cur)
            if not mod:
                break
            parts.append(mod.name)
            cur = mod.parent_id
        parts.reverse()
        return "-".join(parts)

    return {m.id: path_for(m.id) for m in modules}


async def _load_project_modules(db: AsyncSession, project_id: str) -> list[CaseModule]:
    result = await db.execute(
        select(CaseModule).where(CaseModule.project_id == project_id).order_by(CaseModule.sort, CaseModule.name)
    )
    return list(result.scalars().all())


async def _validate_module_parent(
    db: AsyncSession,
    project_id: str,
    module_id: Optional[str],
    parent_id: Optional[str],
) -> None:
    if parent_id is None:
        return
    if module_id and parent_id == module_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot set parent to self",
        )
    parent = await db.get(CaseModule, parent_id)
    if not parent or parent.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid parent module",
        )
    cur: Optional[str] = parent_id
    while cur:
        if module_id and cur == module_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Circular module parent",
            )
        row = await db.get(CaseModule, cur)
        if not row:
            break
        cur = row.parent_id


@router.get("/modules", response_model=list[CaseModuleOut])
async def list_modules(
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CaseModule).where(CaseModule.project_id == ctx.project_id).order_by(CaseModule.sort, CaseModule.name)
    )
    return [CaseModuleOut.model_validate(m) for m in result.scalars().all()]


@router.post("/modules", response_model=CaseModuleOut, status_code=status.HTTP_201_CREATED)
async def create_module(
    body: CaseModuleCreate,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    await _validate_module_parent(db, ctx.project_id, None, body.parent_id)
    mod = CaseModule(project_id=ctx.project_id, name=body.name, parent_id=body.parent_id, sort=body.sort)
    db.add(mod)
    await db.flush()
    await db.refresh(mod)
    return CaseModuleOut.model_validate(mod)


@router.patch("/modules/{module_id}", response_model=CaseModuleOut)
async def update_module(
    module_id: str,
    body: CaseModuleUpdate,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    mod = await db.get(CaseModule, module_id)
    if not mod or mod.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    data = body.model_dump(exclude_unset=True)
    if "parent_id" in data:
        await _validate_module_parent(db, ctx.project_id, module_id, data["parent_id"])
    for k, v in data.items():
        setattr(mod, k, v)
    await db.flush()
    await db.refresh(mod)
    return CaseModuleOut.model_validate(mod)


@router.delete("/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_module(
    module_id: str,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    mod = await db.get(CaseModule, module_id)
    if not mod or mod.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    child_mods = await db.execute(select(CaseModule).where(CaseModule.parent_id == module_id))
    if child_mods.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module has child modules")
    cases = await db.execute(
        select(TestCase).where(TestCase.module_id == module_id, TestCase.deleted.is_(False))
    )
    if cases.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module has cases")
    await db.delete(mod)


@router.get("/import/template")
async def download_case_import_template(
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    await ensure_project_defaults(ctx.project_id, db)
    content = await generate_template_bytes(db, ctx.project_id)
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="case_import_template.xlsx"'},
    )


@router.post("/import", response_model=CaseImportResultOut)
async def import_cases(
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
    result = await parse_import_workbook(
        content,
        project_id=ctx.project_id,
        user_id=ctx.user.id,
        db=db,
    )
    return CaseImportResultOut(
        created=result.created,
        errors=[CaseImportErrorOut(row=e.row, message=e.message) for e in result.errors],
    )


@router.get("", response_model=list[TestCaseOut])
async def list_cases(
    module_id: Optional[str] = None,
    include_submodules: bool = False,
    requirement_id: Optional[str] = None,
    priority: Optional[str] = None,
    q: Optional[str] = None,
    custom_filters: Optional[str] = Query(
        None, description="JSON: { fieldId: value | __empty__ }"
    ),
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    await ensure_project_defaults(ctx.project_id, db)
    tpl = await db.execute(
        select(ProjectFieldTemplate).where(
            ProjectFieldTemplate.project_id == ctx.project_id,
            ProjectFieldTemplate.scene == TemplateScene.functional_case,
        )
    )
    template_row = tpl.scalar_one_or_none()
    template_fields: list = template_row.fields if template_row else []

    parsed_custom: dict[str, str] = {}
    if custom_filters:
        try:
            parsed_custom = parse_custom_filters(custom_filters)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    stmt = select(TestCase).where(TestCase.project_id == ctx.project_id, TestCase.deleted.is_(False))
    modules = await _load_project_modules(db, ctx.project_id)
    path_map = _build_module_path_map(modules)
    if module_id:
        mod = next((m for m in modules if m.id == module_id), None)
        if not mod:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid module")
        if include_submodules:
            filter_ids = {module_id} | _collect_module_descendant_ids(modules, module_id)
            stmt = stmt.where(TestCase.module_id.in_(filter_ids))
        else:
            stmt = stmt.where(TestCase.module_id == module_id)
    if requirement_id and requirement_id != "__empty__":
        req = await db.get(Requirement, requirement_id)
        if not req or req.project_id != ctx.project_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid requirement")
    stmt = apply_case_list_filters(
        stmt,
        q=q,
        priority=priority,
        requirement_id=requirement_id,
        template_fields=template_fields,
        custom_filters=parsed_custom or None,
    )
    result = await db.execute(stmt.order_by(TestCase.updated_at.desc()))
    out: list[TestCaseOut] = []
    for c in result.scalars().all():
        out.append(await case_out(c, db, module_path=path_map.get(c.module_id)))
    return out


@router.post("", response_model=TestCaseOut, status_code=status.HTTP_201_CREATED)
async def create_case(
    body: TestCaseCreate,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    await ensure_project_defaults(ctx.project_id, db)
    mod = await db.get(CaseModule, body.module_id)
    if not mod or mod.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid module")
    try:
        await validate_requirement_ids(db, ctx.project_id, body.requirement_ids)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    tpl = await db.execute(
        select(ProjectFieldTemplate).where(
            ProjectFieldTemplate.project_id == ctx.project_id,
            ProjectFieldTemplate.scene == TemplateScene.functional_case,
        )
    )
    fields_schema = tpl.scalar_one().fields
    member_ids = await load_project_member_user_ids(db, ctx.project_id)
    custom = validate_custom_fields(
        fields_schema,
        body.custom_fields,
        project_id=ctx.project_id,
        project_member_ids=member_ids,
    )
    case = TestCase(
        project_id=ctx.project_id,
        module_id=body.module_id,
        title=body.title,
        priority=body.priority,
        precondition=body.precondition,
        step_text=body.step_text,
        expected_result=body.expected_result,
        steps=[],
        tags=body.tags,
        custom_fields=custom,
        created_by=ctx.user.id,
    )
    db.add(case)
    await db.flush()
    await set_case_requirements(db, case.id, body.requirement_ids)
    await db.refresh(case)
    modules = await _load_project_modules(db, ctx.project_id)
    path_map = _build_module_path_map(modules)
    return await case_out(case, db, module_path=path_map.get(case.module_id))


@router.get("/{case_id}", response_model=TestCaseOut)
async def get_case(
    case_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    case = await db.get(TestCase, case_id)
    if not case or case.project_id != ctx.project_id or case.deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    modules = await _load_project_modules(db, ctx.project_id)
    path_map = _build_module_path_map(modules)
    return await case_out(case, db, module_path=path_map.get(case.module_id))


@router.patch("/{case_id}", response_model=TestCaseOut)
async def update_case(
    case_id: str,
    body: TestCaseUpdate,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    case = await db.get(TestCase, case_id)
    if not case or case.project_id != ctx.project_id or case.deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    old_file_keys = file_keys_from_case(case)
    data = body.model_dump(exclude_unset=True)
    req_ids = data.pop("requirement_ids", None)
    if req_ids is not None:
        try:
            await validate_requirement_ids(db, ctx.project_id, req_ids)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if "custom_fields" in data:
        tpl = await db.execute(
            select(ProjectFieldTemplate).where(
                ProjectFieldTemplate.project_id == ctx.project_id,
                ProjectFieldTemplate.scene == TemplateScene.functional_case,
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
        setattr(case, k, v)
    await db.flush()
    if req_ids is not None:
        await set_case_requirements(db, case.id, req_ids)
    content_changed = any(
        k in data
        for k in ("precondition", "step_text", "expected_result", "custom_fields")
    )
    if content_changed:
        await cleanup_after_case_content_change(
            db, ctx.project_id, case, old_file_keys, file_keys_from_case(case)
        )
    await db.refresh(case)
    modules = await _load_project_modules(db, ctx.project_id)
    path_map = _build_module_path_map(modules)
    return await case_out(case, db, module_path=path_map.get(case.module_id))


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: str,
    ctx: ProjectContext = Depends(require_project_context_tester),
    db: AsyncSession = Depends(get_db),
):
    case = await db.get(TestCase, case_id)
    if not case or case.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    await cleanup_after_case_deleted(db, ctx.project_id, case)
    case.deleted = True
