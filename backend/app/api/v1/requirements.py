from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import ProjectContext, require_project_context, require_project_context_catalog
from app.models.project_version import ProjectVersion
from app.models.requirement import Requirement, RequirementStatus
from app.schemas.requirement import RequirementCreate, RequirementOut, RequirementUpdate
from app.schemas.version import VersionBrief
from app.services.versions import validate_version_id

router = APIRouter(prefix="/requirements", tags=["requirements"])


async def _requirement_out(row: Requirement, db: AsyncSession) -> RequirementOut:
    version = None
    if row.version_id:
        v = await db.get(ProjectVersion, row.version_id)
        if v:
            version = VersionBrief(id=v.id, num=v.num, name=v.name)
    return RequirementOut(
        id=row.id,
        project_id=row.project_id,
        num=row.num,
        title=row.title,
        external_url=row.external_url,
        version_id=row.version_id,
        version=version,
        status=row.status,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def _next_req_num(project_id: str, db: AsyncSession) -> int:
    result = await db.execute(select(func.max(Requirement.num)).where(Requirement.project_id == project_id))
    return (result.scalar() or 0) + 1


@router.get("", response_model=list[RequirementOut])
async def list_requirements(
    version_id: Optional[str] = None,
    status: Optional[RequirementStatus] = None,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Requirement).where(Requirement.project_id == ctx.project_id)
    if version_id is not None:
        stmt = stmt.where(Requirement.version_id == version_id)
    if status is not None:
        stmt = stmt.where(Requirement.status == status)
    result = await db.execute(stmt.order_by(Requirement.num.desc()))
    rows = result.scalars().all()
    return [await _requirement_out(r, db) for r in rows]


@router.post("", response_model=RequirementOut, status_code=status.HTTP_201_CREATED)
async def create_requirement(
    body: RequirementCreate,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    try:
        await validate_version_id(db, ctx.project_id, body.version_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    row = Requirement(
        project_id=ctx.project_id,
        num=await _next_req_num(ctx.project_id, db),
        title=body.title,
        external_url=body.external_url,
        version_id=body.version_id,
        status=body.status,
        created_by=ctx.user.id,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return await _requirement_out(row, db)


@router.get("/{requirement_id}", response_model=RequirementOut)
async def get_requirement(
    requirement_id: str,
    ctx: ProjectContext = Depends(require_project_context),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(Requirement, requirement_id)
    if not row or row.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")
    return await _requirement_out(row, db)


@router.patch("/{requirement_id}", response_model=RequirementOut)
async def update_requirement(
    requirement_id: str,
    body: RequirementUpdate,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(Requirement, requirement_id)
    if not row or row.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")
    data = body.model_dump(exclude_unset=True)
    if "version_id" in data:
        try:
            await validate_version_id(db, ctx.project_id, data.get("version_id"))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    for k, v in data.items():
        setattr(row, k, v)
    await db.flush()
    await db.refresh(row)
    return await _requirement_out(row, db)


@router.delete("/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_requirement(
    requirement_id: str,
    ctx: ProjectContext = Depends(require_project_context_catalog),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(Requirement, requirement_id)
    if not row or row.project_id != ctx.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")
    await db.delete(row)
