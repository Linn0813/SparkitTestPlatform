from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.version_types import VERSION_TYPES
from app.core.database import get_db
from app.core.deps import ProjectContext, require_project_context, require_project_context_catalog
from app.models.project_version import ProjectVersion
from app.schemas.version import (
    ProjectVersionCreate,
    ProjectVersionOut,
    ProjectVersionUpdate,
    VersionNodeCompleteOut,
    VersionNodeUpdate,
)
from app.services.links import validate_project_member_ids
from app.services.version_serializers import version_to_out
from app.services.version_wecom_notify import notify_version_node_complete
from app.services.version_workflow import (
    VersionWorkflowError,
    complete_version_node,
    ensure_version_workflow_nodes_started,
    init_version_workflow,
    reopen_version_node,
    resync_version_workflow_on_type_change,
    update_version_node_metadata,
)
from app.services.versions import count_version_references

router = APIRouter(prefix="/versions", tags=["versions"])


async def _next_version_num(project_id: str, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.max(ProjectVersion.num)).where(ProjectVersion.project_id == project_id)
    )
    return (result.scalar() or 0) + 1


async def _get_version_or_404(version_id: str, ctx: ProjectContext, db: AsyncSession) -> ProjectVersion:
    row = await db.get(ProjectVersion, version_id)
    if not row or row.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    return row


@router.get("", response_model=list[ProjectVersionOut])
async def list_versions(
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProjectVersion)
        .where(ProjectVersion.project_id == ctx.project_id)
        .order_by(ProjectVersion.num.desc())
    )
    versions = result.scalars().all()
    return [await version_to_out(db, v) for v in versions]


@router.post("", response_model=ProjectVersionOut, status_code=status.HTTP_201_CREATED)
async def create_version(
    body: ProjectVersionCreate,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    if body.version_type not in VERSION_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid version type")
    row = ProjectVersion(
        project_id=ctx.project_id,
        num=await _next_version_num(ctx.project_id, db),
        name=body.name.strip(),
        build_number=(body.build_number.strip() or None) if body.build_number else None,
        version_type=body.version_type,
        released_at=body.released_at,
        created_by=ctx.user.id,
    )
    db.add(row)
    try:
        await db.flush()
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Version name already exists in this project",
        ) from e
    await init_version_workflow(db, row.id, ctx.project_id, body.version_type)
    await ensure_version_workflow_nodes_started(db, row, actor_id=ctx.user.id)
    await db.refresh(row)
    return await version_to_out(db, row)


@router.get("/{version_id}", response_model=ProjectVersionOut)
async def get_version(
    version_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_version_or_404(version_id, ctx, db)
    await ensure_version_workflow_nodes_started(db, row, actor_id=ctx.user.id)
    return await version_to_out(db, row)


@router.patch("/{version_id}", response_model=ProjectVersionOut)
async def update_version(
    version_id: str,
    body: ProjectVersionUpdate,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_version_or_404(version_id, ctx, db)
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    new_type = data.pop("version_type", None)
    if new_type is not None and new_type not in VERSION_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid version type")

    if "name" in data and data["name"] is not None:
        row.name = data["name"].strip()
    if "build_number" in data:
        bn = data["build_number"]
        if isinstance(bn, str):
            bn = bn.strip() or None
        row.build_number = bn
    if "released_at" in data:
        row.released_at = data["released_at"]

    type_changed = new_type is not None and new_type != row.version_type
    if type_changed:
        await resync_version_workflow_on_type_change(db, row, new_type)

    try:
        await db.flush()
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Version name already exists in this project",
        ) from e
    await db.refresh(row)
    return await version_to_out(db, row)


@router.delete("/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_version(
    version_id: str,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_version_or_404(version_id, ctx, db)
    refs = await count_version_references(db, version_id)
    if refs > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Version is referenced by {refs} record(s); unlink first",
        )
    await db.delete(row)


@router.patch("/{version_id}/nodes/{node_key}", response_model=ProjectVersionOut)
async def update_version_node_endpoint(
    version_id: str,
    node_key: str,
    body: VersionNodeUpdate,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_version_or_404(version_id, ctx, db)
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    if "assignee_id" in updates and updates["assignee_id"]:
        try:
            await validate_project_member_ids(db, ctx.project_id, [updates["assignee_id"]])
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    try:
        await update_version_node_metadata(db, row, node_key, updates)
    except VersionWorkflowError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    await db.refresh(row)
    return await version_to_out(db, row)


@router.post("/{version_id}/nodes/{node_key}/complete", response_model=VersionNodeCompleteOut)
async def complete_version_node_endpoint(
    version_id: str,
    node_key: str,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_version_or_404(version_id, ctx, db)
    try:
        await complete_version_node(db, row, node_key, ctx.user.id)
    except VersionWorkflowError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    await db.refresh(row)
    mention_count = await notify_version_node_complete(db, row, node_key, ctx.user.id)
    out = await version_to_out(db, row)
    return VersionNodeCompleteOut(version=out, wecom_mention_count=mention_count)


@router.post("/{version_id}/nodes/{node_key}/reopen", response_model=ProjectVersionOut)
async def reopen_version_node_endpoint(
    version_id: str,
    node_key: str,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_version_or_404(version_id, ctx, db)
    try:
        await reopen_version_node(db, row, node_key)
    except VersionWorkflowError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    await db.refresh(row)
    return await version_to_out(db, row)
