from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_project_access, require_system_admin
from app.core.project_permissions import user_can_manage_project_settings
from app.core.project_roles import member_is_project_admin
from app.models.project import BusinessProjectRole, Project, ProjectMember
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectMemberAdd,
    ProjectMemberOut,
    ProjectMemberUpdate,
    ProjectOut,
    ProjectUpdate,
)
from app.schemas.upload import FileUrlOut, ProjectUploadOut
from app.schemas.user import UserOut
from app.services.file_storage import (
    build_file_download_url,
    media_kind_from_content_type,
    upload_project_bytes,
)
from app.services.project_delete import delete_project_cascade
from app.services.project_setup import ensure_project_defaults

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.is_system_admin:
        result = await db.execute(select(Project).order_by(Project.created_at.desc()))
        return [ProjectOut.model_validate(p) for p in result.scalars().all()]

    member_result = await db.execute(
        select(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user.id)
        .order_by(Project.created_at.desc())
    )
    return [ProjectOut.model_validate(p) for p in member_result.scalars().unique().all()]


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    user: User = Depends(require_system_admin),
    db: AsyncSession = Depends(get_db),
):
    project = Project(name=body.name)
    db.add(project)
    await db.flush()
    db.add(
        ProjectMember(
            project_id=project.id,
            user_id=user.id,
            role=BusinessProjectRole.member,
            is_project_admin=True,
        )
    )
    await db.flush()
    await ensure_project_defaults(project.id, db)
    await db.refresh(project)
    return ProjectOut.model_validate(project)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not user.is_system_admin:
        m = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id, ProjectMember.user_id == user.id
            )
        )
        if not m.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access")
    return ProjectOut.model_validate(project)


async def _require_project_manage(project_id: str, user: User, db: AsyncSession) -> None:
    if not await user_can_manage_project_settings(user, project_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project admin required")


async def _ensure_not_last_project_admin(
    db: AsyncSession, project_id: str, member: ProjectMember
) -> None:
    if not member_is_project_admin(member):
        return
    result = await db.execute(select(ProjectMember).where(ProjectMember.project_id == project_id))
    admins = [m for m in result.scalars().all() if member_is_project_admin(m)]
    if len(admins) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove or demote the last project admin",
        )


def _member_out(member: ProjectMember, user: Optional[User]) -> ProjectMemberOut:
    return ProjectMemberOut(
        id=member.id,
        project_id=member.project_id,
        user_id=member.user_id,
        role=member.role,
        is_project_admin=member.is_project_admin,
        user=UserOut.model_validate(user) if user else None,
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    user: User = Depends(require_system_admin),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    await delete_project_cascade(db, project)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_project_manage(project_id, user, db)
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if body.name is not None:
        project.name = body.name
    if body.is_enabled is not None:
        project.is_enabled = body.is_enabled
    await db.flush()
    await db.refresh(project)
    return ProjectOut.model_validate(project)


@router.get("/{project_id}/members", response_model=list[ProjectMemberOut])
async def list_project_members(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not user.is_system_admin:
        pm = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id, ProjectMember.user_id == user.id
            )
        )
        if not pm.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access")
    result = await db.execute(select(ProjectMember).where(ProjectMember.project_id == project_id))
    out: list[ProjectMemberOut] = []
    for m in result.scalars().all():
        u = await db.get(User, m.user_id)
        out.append(_member_out(m, u))
    return out


@router.post("/{project_id}/members", response_model=ProjectMemberOut, status_code=status.HTTP_201_CREATED)
async def add_project_member(
    project_id: str,
    body: ProjectMemberAdd,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_project_manage(project_id, user, db)
    existing = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == body.user_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already a member")
    member = ProjectMember(
        project_id=project_id,
        user_id=body.user_id,
        role=body.role,
        is_project_admin=body.is_project_admin,
    )
    db.add(member)
    await db.flush()
    u = await db.get(User, body.user_id)
    return _member_out(member, u)


MAX_UPLOAD_BYTES = 50 * 1024 * 1024
ALLOWED_UPLOAD_TYPES = ("image/", "video/")


@router.post("/{project_id}/uploads", response_model=ProjectUploadOut, status_code=status.HTTP_201_CREATED)
async def upload_project_file(
    project_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    await require_project_access(project_id, user, db)
    content_type = file.content_type or "application/octet-stream"
    if not any(content_type.startswith(p) for p in ALLOWED_UPLOAD_TYPES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持上传图片或视频",
        )
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件过大（最大 50MB）")
    filename = file.filename or "upload.bin"
    object_key, size = await upload_project_bytes(db, project_id, data, filename, content_type)
    return ProjectUploadOut(
        object_key=object_key,
        filename=filename,
        size=size,
        content_type=content_type,
        kind=media_kind_from_content_type(content_type),
        url=build_file_download_url(object_key),
    )


@router.get("/{project_id}/files/url", response_model=FileUrlOut)
async def get_project_file_url(
    project_id: str,
    object_key: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    await require_project_access(project_id, user, db)
    prefix = f"projects/{project_id}/"
    if not object_key.startswith(prefix):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file key")
    return FileUrlOut(url=build_file_download_url(object_key))


@router.patch("/{project_id}/members/{member_id}", response_model=ProjectMemberOut)
async def update_project_member(
    project_id: str,
    member_id: str,
    body: ProjectMemberUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_project_manage(project_id, user, db)
    member = await db.get(ProjectMember, member_id)
    if not member or member.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    if body.is_project_admin is not None or body.role is not None:
        old_is_admin = member.is_project_admin
        new_is_admin = body.is_project_admin if body.is_project_admin is not None else old_is_admin
        if old_is_admin and not new_is_admin:
            await _ensure_not_last_project_admin(db, project_id, member)
        if body.is_project_admin is not None:
            member.is_project_admin = body.is_project_admin
        if body.role is not None:
            member.role = body.role
    await db.flush()
    u = await db.get(User, member.user_id)
    return _member_out(member, u)


@router.delete("/{project_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    project_id: str,
    member_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_project_manage(project_id, user, db)
    member = await db.get(ProjectMember, member_id)
    if not member or member.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    await _ensure_not_last_project_admin(db, project_id, member)
    await db.delete(member)
