from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import ProjectContext, require_project_context, require_project_context_catalog
from app.models.project_version import ProjectVersion
from app.schemas.version import ProjectVersionCreate, ProjectVersionOut, ProjectVersionUpdate
from app.services.versions import count_version_references

router = APIRouter(prefix="/versions", tags=["versions"])


async def _next_version_num(project_id: str, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.max(ProjectVersion.num)).where(ProjectVersion.project_id == project_id)
    )
    return (result.scalar() or 0) + 1


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
    return [ProjectVersionOut.model_validate(r) for r in result.scalars().all()]


@router.post("", response_model=ProjectVersionOut, status_code=status.HTTP_201_CREATED)
async def create_version(
    body: ProjectVersionCreate,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    row = ProjectVersion(
        project_id=ctx.project_id,
        num=await _next_version_num(ctx.project_id, db),
        name=body.name.strip(),
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
    await db.refresh(row)
    return ProjectVersionOut.model_validate(row)


@router.get("/{version_id}", response_model=ProjectVersionOut)
async def get_version(
    version_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(ProjectVersion, version_id)
    if not row or row.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    return ProjectVersionOut.model_validate(row)


@router.patch("/{version_id}", response_model=ProjectVersionOut)
async def update_version(
    version_id: str,
    body: ProjectVersionUpdate,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(ProjectVersion, version_id)
    if not row or row.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    if "name" in data and data["name"] is not None:
        row.name = data["name"].strip()
    if "released_at" in data:
        row.released_at = data["released_at"]
    try:
        await db.flush()
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Version name already exists in this project",
        ) from e
    await db.refresh(row)
    return ProjectVersionOut.model_validate(row)


@router.delete("/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_version(
    version_id: str,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(ProjectVersion, version_id)
    if not row or row.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    refs = await count_version_references(db, version_id)
    if refs > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Version is referenced by {refs} record(s); unlink first",
        )
    await db.delete(row)
