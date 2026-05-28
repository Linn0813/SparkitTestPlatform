from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.version_types import VERSION_TYPES
from app.core.database import get_db
from app.core.deps import (
    ProjectContext,
    require_project_context,
    require_project_context_admin,
    require_project_context_catalog,
)
from app.models.version_workflow import VersionNodeProgress
from app.models.requirement import RequirementNodeProgress
from app.models.template import (
    BugStatus,
    ProjectFieldTemplate,
    ProjectIntegration,
    RequirementOptionDef,
    RequirementRoleDef,
    RequirementWorkflowNodeDef,
    TemplateScene,
    VersionWorkflowNodeDef,
)
from app.schemas.requirement import (
    RequirementStatusRuleOut,
    RequirementStatusRulesReplaceBody,
    RequirementStatusSyncBatchOut,
    RequirementWorkflowNodeDefCreate,
    RequirementWorkflowNodeDefOut,
    RequirementWorkflowNodeDefUpdate,
    RequirementWorkflowNodeReorderBody,
)
from app.schemas.version import (
    VersionStatusRuleOut,
    VersionStatusRulesReplaceBody,
    VersionStatusSyncBatchOut,
    VersionWorkflowNodeDefCreate,
    VersionWorkflowNodeDefOut,
    VersionWorkflowNodeDefUpdate,
    VersionWorkflowNodeReorderBody,
)
from app.schemas.template import (
    BugStatusCreate,
    BugStatusOut,
    BugStatusUpdate,
    FieldTemplateOut,
    FieldTemplateUpdate,
    RequirementOptionDefCreate,
    RequirementOptionDefOut,
    RequirementOptionDefUpdate,
    RequirementRoleDefCreate,
    RequirementRoleDefOut,
    RequirementRoleDefUpdate,
    WecomIntegrationOut,
    WecomIntegrationUpdate,
    WecomTestRequest,
)
from app.services.project_setup import ensure_project_defaults
from app.services.requirement_config import (
    OPTION_CATEGORIES,
    count_option_usage,
    count_options_in_category,
    count_role_usage_in_requirements,
    count_role_usage_in_workflow,
    ensure_project_option_defs,
    ensure_project_role_defs,
    load_project_option_defs,
    load_project_role_defs,
    rename_role_key_in_project,
    validate_option_key_format,
    validate_role_key_format,
)
from app.services.requirement_nodes import sync_project_requirement_statuses
from app.services.requirement_status_rules import (
    ensure_project_status_rules,
    load_project_status_rules,
    replace_project_status_rules,
)
from app.services.requirement_workflow import (
    assert_workflow_node_deletable,
    ensure_project_workflow_defs,
    load_project_workflow_defs,
    new_custom_node_key,
    sync_lane_fields,
    sync_progress_for_new_def,
    validate_lane_indexes,
    validate_role_keys_for_project,
)
from app.services.template_fields import validate_template_fields
from app.services.version_workflow import (
    VersionWorkflowError,
    assert_version_workflow_node_deletable,
    delete_version_node_progress_for_def,
    sync_project_version_statuses,
    sync_version_progress_for_new_def,
)
from app.services.version_status_rules import (
    ensure_project_version_status_rules,
    replace_project_version_status_rules,
)
from app.services.version_workflow_defs import (
    ensure_project_version_workflow_defs,
    load_project_version_workflow_defs,
    sync_lane_fields as sync_version_lane_fields,
    validate_lane_indexes as validate_version_lane_indexes,
)

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


@router.get("/{project_id}/requirement-roles", response_model=list[RequirementRoleDefOut])
async def list_requirement_roles(
    project_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    await ensure_project_defaults(project_id, db)
    roles = await load_project_role_defs(db, project_id)
    return [RequirementRoleDefOut.model_validate(r) for r in roles]


@router.post(
    "/{project_id}/requirement-roles",
    response_model=RequirementRoleDefOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_requirement_role(
    project_id: str,
    body: RequirementRoleDefCreate,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    role_key = body.role_key.strip()
    try:
        validate_role_key_format(role_key)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    existing = await db.execute(
        select(RequirementRoleDef).where(
            RequirementRoleDef.project_id == project_id,
            RequirementRoleDef.role_key == role_key,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="角色标识已存在")
    row = RequirementRoleDef(
        project_id=project_id,
        role_key=role_key,
        label=body.label.strip(),
        sort=body.sort,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return RequirementRoleDefOut.model_validate(row)


@router.patch("/{project_id}/requirement-roles/{role_id}", response_model=RequirementRoleDefOut)
async def update_requirement_role(
    project_id: str,
    role_id: str,
    body: RequirementRoleDefUpdate,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    row = await db.get(RequirementRoleDef, role_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    data = body.model_dump(exclude_unset=True)
    if "role_key" in data and data["role_key"] is not None:
        new_key = data["role_key"].strip()
        try:
            validate_role_key_format(new_key)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        if new_key != row.role_key:
            dup = await db.execute(
                select(RequirementRoleDef).where(
                    RequirementRoleDef.project_id == project_id,
                    RequirementRoleDef.role_key == new_key,
                    RequirementRoleDef.id != role_id,
                )
            )
            if dup.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="角色标识已存在")
            await rename_role_key_in_project(db, project_id, row.role_key, new_key)
            row.role_key = new_key
            data.pop("role_key", None)
    if "label" in data and data["label"] is not None:
        row.label = data["label"].strip()
    if "sort" in data and data["sort"] is not None:
        row.sort = data["sort"]
    await db.flush()
    await db.refresh(row)
    return RequirementRoleDefOut.model_validate(row)


@router.delete("/{project_id}/requirement-roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_requirement_role(
    project_id: str,
    role_id: str,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    row = await db.get(RequirementRoleDef, role_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    total = await db.execute(
        select(func.count()).select_from(RequirementRoleDef).where(RequirementRoleDef.project_id == project_id)
    )
    if (total.scalar() or 0) <= 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少保留一个角色")
    wf_count = await count_role_usage_in_workflow(db, project_id, row.role_key)
    if wf_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"角色被 {wf_count} 个工作流节点引用，请先解除关联",
        )
    req_count = await count_role_usage_in_requirements(db, project_id, row.role_key)
    if req_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"角色被 {req_count} 个需求的人员配置引用，请先调整",
        )
    await db.delete(row)


@router.get("/{project_id}/requirement-options", response_model=list[RequirementOptionDefOut])
async def list_requirement_options(
    project_id: str,
    category: Optional[str] = None,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    if category is not None and category not in OPTION_CATEGORIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category")
    await ensure_project_defaults(project_id, db)
    options = await load_project_option_defs(db, project_id, category)
    return [RequirementOptionDefOut.model_validate(o) for o in options]


@router.post(
    "/{project_id}/requirement-options",
    response_model=RequirementOptionDefOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_requirement_option(
    project_id: str,
    body: RequirementOptionDefCreate,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    category = body.category.strip()
    if category not in OPTION_CATEGORIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category")
    option_key = body.option_key.strip()
    try:
        validate_option_key_format(option_key)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    existing = await db.execute(
        select(RequirementOptionDef).where(
            RequirementOptionDef.project_id == project_id,
            RequirementOptionDef.category == category,
            RequirementOptionDef.option_key == option_key,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="选项标识已存在")
    row = RequirementOptionDef(
        project_id=project_id,
        category=category,
        option_key=option_key,
        label=body.label.strip(),
        sort=body.sort,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return RequirementOptionDefOut.model_validate(row)


@router.patch(
    "/{project_id}/requirement-options/{option_id}",
    response_model=RequirementOptionDefOut,
)
async def update_requirement_option(
    project_id: str,
    option_id: str,
    body: RequirementOptionDefUpdate,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    row = await db.get(RequirementOptionDef, option_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option not found")
    data = body.model_dump(exclude_unset=True)
    if "option_key" in data and data["option_key"] is not None:
        new_key = data["option_key"].strip()
        try:
            validate_option_key_format(new_key)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        if new_key != row.option_key:
            dup = await db.execute(
                select(RequirementOptionDef).where(
                    RequirementOptionDef.project_id == project_id,
                    RequirementOptionDef.category == row.category,
                    RequirementOptionDef.option_key == new_key,
                    RequirementOptionDef.id != option_id,
                )
            )
            if dup.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="选项标识已存在")
            in_use = await count_option_usage(db, project_id, row.category, row.option_key)
            if in_use > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"选项被 {in_use} 个需求引用，无法修改标识",
                )
            row.option_key = new_key
            data.pop("option_key", None)
    if "label" in data and data["label"] is not None:
        row.label = data["label"].strip()
    if "sort" in data and data["sort"] is not None:
        row.sort = data["sort"]
    await db.flush()
    await db.refresh(row)
    return RequirementOptionDefOut.model_validate(row)


@router.delete("/{project_id}/requirement-options/{option_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_requirement_option(
    project_id: str,
    option_id: str,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    row = await db.get(RequirementOptionDef, option_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option not found")
    total = await count_options_in_category(db, project_id, row.category)
    if total <= 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="每类选项至少保留一项")
    in_use = await count_option_usage(db, project_id, row.category, row.option_key)
    if in_use > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"选项被 {in_use} 个需求引用，请先调整需求",
        )
    await db.delete(row)


@router.get("/{project_id}/requirement-workflow-nodes", response_model=list[RequirementWorkflowNodeDefOut])
async def list_requirement_workflow_nodes(
    project_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    defs = await ensure_project_workflow_defs(db, project_id)
    return [RequirementWorkflowNodeDefOut.model_validate(d) for d in defs]


@router.post(
    "/{project_id}/requirement-workflow-nodes",
    response_model=RequirementWorkflowNodeDefOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_requirement_workflow_node(
    project_id: str,
    body: RequirementWorkflowNodeDefCreate,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    try:
        await validate_role_keys_for_project(db, project_id, body.role_keys)
        validate_lane_indexes(body.lane_indexes)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    node_key = new_custom_node_key()
    row = RequirementWorkflowNodeDef(
        project_id=project_id,
        node_key=node_key,
        label=body.label,
        role_keys=body.role_keys,
        lane_indexes=sorted(set(body.lane_indexes)),
        blocks_lane_gate=body.blocks_lane_gate,
        sort_in_lane=body.sort_in_lane,
    )
    sync_lane_fields(row)
    db.add(row)
    await db.flush()
    await sync_progress_for_new_def(db, project_id, node_key)
    return RequirementWorkflowNodeDefOut.model_validate(row)


@router.patch(
    "/{project_id}/requirement-workflow-nodes/{def_id}",
    response_model=RequirementWorkflowNodeDefOut,
)
async def update_requirement_workflow_node(
    project_id: str,
    def_id: str,
    body: RequirementWorkflowNodeDefUpdate,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    row = await db.get(RequirementWorkflowNodeDef, def_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    data = body.model_dump(exclude_unset=True)
    if "role_keys" in data and data["role_keys"] is not None:
        try:
            await validate_role_keys_for_project(db, project_id, data["role_keys"])
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if "lane_indexes" in data and data["lane_indexes"] is not None:
        try:
            validate_lane_indexes(data["lane_indexes"])
            data["lane_indexes"] = sorted(set(data["lane_indexes"]))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    for k, v in data.items():
        setattr(row, k, v)
    sync_lane_fields(row)
    await db.flush()
    return RequirementWorkflowNodeDefOut.model_validate(row)


@router.delete("/{project_id}/requirement-workflow-nodes/{def_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_requirement_workflow_node(
    project_id: str,
    def_id: str,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import delete

    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    row = await db.get(RequirementWorkflowNodeDef, def_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    try:
        await assert_workflow_node_deletable(db, row.node_key)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    await db.execute(
        delete(RequirementNodeProgress).where(RequirementNodeProgress.node_key == row.node_key)
    )
    await db.delete(row)


@router.put("/{project_id}/requirement-workflow-nodes/reorder", response_model=list[RequirementWorkflowNodeDefOut])
async def reorder_requirement_workflow_nodes(
    project_id: str,
    body: RequirementWorkflowNodeReorderBody,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    id_map = {item.id: item for item in body.items}
    defs = await load_project_workflow_defs(db, project_id)
    for d in defs:
        if d.id in id_map:
            item = id_map[d.id]
            d.lane_indexes = [item.lane_index]
            d.sort_in_lane = item.sort_in_lane
            sync_lane_fields(d)
    await db.flush()
    defs = await load_project_workflow_defs(db, project_id)
    return [RequirementWorkflowNodeDefOut.model_validate(d) for d in defs]


@router.get("/{project_id}/version-workflow-nodes", response_model=list[VersionWorkflowNodeDefOut])
async def list_version_workflow_nodes(
    project_id: str,
    version_type: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    if version_type not in VERSION_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid version type")
    defs = await ensure_project_version_workflow_defs(db, project_id, version_type)
    return [VersionWorkflowNodeDefOut.model_validate(d) for d in defs]


@router.post(
    "/{project_id}/version-workflow-nodes",
    response_model=VersionWorkflowNodeDefOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_version_workflow_node(
    project_id: str,
    version_type: str,
    body: VersionWorkflowNodeDefCreate,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    if version_type not in VERSION_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid version type")
    try:
        validate_version_lane_indexes(body.lane_indexes)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    row = VersionWorkflowNodeDef(
        project_id=project_id,
        version_type=version_type,
        node_key=body.node_key.strip(),
        label=body.label.strip(),
        lane_indexes=sorted(set(body.lane_indexes)),
        sort_in_lane=body.sort_in_lane,
    )
    sync_version_lane_fields(row)
    db.add(row)
    try:
        await db.flush()
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Node key already exists for this version type",
        ) from e
    await sync_version_progress_for_new_def(db, project_id, version_type, row.node_key)
    return VersionWorkflowNodeDefOut.model_validate(row)


@router.patch(
    "/{project_id}/version-workflow-nodes/{def_id}",
    response_model=VersionWorkflowNodeDefOut,
)
async def update_version_workflow_node(
    project_id: str,
    def_id: str,
    body: VersionWorkflowNodeDefUpdate,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    row = await db.get(VersionWorkflowNodeDef, def_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    data = body.model_dump(exclude_unset=True)
    if "lane_indexes" in data and data["lane_indexes"] is not None:
        try:
            validate_version_lane_indexes(data["lane_indexes"])
            data["lane_indexes"] = sorted(set(data["lane_indexes"]))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    for k, v in data.items():
        setattr(row, k, v)
    sync_version_lane_fields(row)
    await db.flush()
    return VersionWorkflowNodeDefOut.model_validate(row)


@router.delete("/{project_id}/version-workflow-nodes/{def_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_version_workflow_node(
    project_id: str,
    def_id: str,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import delete

    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    row = await db.get(VersionWorkflowNodeDef, def_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    try:
        await assert_version_workflow_node_deletable(
            db, project_id, row.version_type, row.node_key
        )
    except VersionWorkflowError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    await delete_version_node_progress_for_def(
        db, project_id, row.version_type, row.node_key
    )
    await db.delete(row)


@router.put("/{project_id}/version-workflow-nodes/reorder", response_model=list[VersionWorkflowNodeDefOut])
async def reorder_version_workflow_nodes(
    project_id: str,
    version_type: str,
    body: VersionWorkflowNodeReorderBody,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    if version_type not in VERSION_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid version type")
    id_map = {item.id: item for item in body.items}
    defs = await load_project_version_workflow_defs(db, project_id, version_type)
    for d in defs:
        if d.id in id_map:
            item = id_map[d.id]
            d.lane_indexes = [item.lane_index]
            d.sort_in_lane = item.sort_in_lane
            sync_version_lane_fields(d)
    await db.flush()
    defs = await load_project_version_workflow_defs(db, project_id, version_type)
    return [VersionWorkflowNodeDefOut.model_validate(d) for d in defs]


@router.get("/{project_id}/requirement-status-rules", response_model=list[RequirementStatusRuleOut])
async def list_requirement_status_rules(
    project_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    await ensure_project_workflow_defs(db, project_id)
    rules = await ensure_project_status_rules(db, project_id)
    return [RequirementStatusRuleOut.model_validate(r) for r in rules]


@router.put("/{project_id}/requirement-status-rules", response_model=list[RequirementStatusRuleOut])
async def replace_requirement_status_rules_api(
    project_id: str,
    body: RequirementStatusRulesReplaceBody,
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    defs = await ensure_project_workflow_defs(db, project_id)
    try:
        rules = await replace_project_status_rules(
            db,
            project_id,
            [item.model_dump() for item in body.rules],
            workflow_defs=defs,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return [RequirementStatusRuleOut.model_validate(r) for r in rules]


@router.post("/{project_id}/requirements/sync-statuses", response_model=RequirementStatusSyncBatchOut)
async def sync_project_requirement_statuses_api(
    project_id: str,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    updated_count = await sync_project_requirement_statuses(db, project_id, actor_id=ctx.user.id)
    return RequirementStatusSyncBatchOut(updated_count=updated_count)


@router.get("/{project_id}/version-status-rules", response_model=list[VersionStatusRuleOut])
async def list_version_status_rules(
    project_id: str,
    version_type: str = Query(default="app_release"),
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    if version_type not in VERSION_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"未知版本类型：{version_type}")
    await ensure_project_version_workflow_defs(db, project_id, version_type)
    try:
        rules = await ensure_project_version_status_rules(db, project_id, version_type)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return [VersionStatusRuleOut.model_validate(r) for r in rules]


@router.put("/{project_id}/version-status-rules", response_model=list[VersionStatusRuleOut])
async def replace_version_status_rules_api(
    project_id: str,
    body: VersionStatusRulesReplaceBody,
    version_type: str = Query(default="app_release"),
    ctx: ProjectContext = Depends(require_project_context_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    if version_type not in VERSION_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"未知版本类型：{version_type}")
    await ensure_project_version_workflow_defs(db, project_id, version_type)
    defs = await load_project_version_workflow_defs(db, project_id, version_type)
    try:
        rules = await replace_project_version_status_rules(
            db,
            project_id,
            version_type,
            [r.model_dump() for r in body.rules],
            workflow_defs=defs,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return [VersionStatusRuleOut.model_validate(r) for r in rules]


@router.post("/{project_id}/versions/sync-statuses", response_model=VersionStatusSyncBatchOut)
async def sync_project_version_statuses_api(
    project_id: str,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    if ctx.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project mismatch")
    updated_count = await sync_project_version_statuses(db, project_id)
    return VersionStatusSyncBatchOut(updated_count=updated_count)


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
        app_public_url=row.app_public_url,
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
        if k == "app_public_url":
            v = (v or "").strip() or None
        setattr(row, k, v)
    await db.flush()
    return WecomIntegrationOut(
        project_id=project_id,
        wecom_webhook_url=row.wecom_webhook_url,
        wecom_enabled=row.wecom_enabled,
        app_public_url=row.app_public_url,
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
