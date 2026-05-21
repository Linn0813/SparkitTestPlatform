from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, user_can_access_project
from app.core.security import create_access_token, verify_password
from app.models.project import Project, ProjectMember
from app.models.user import User
from app.schemas.auth import LoginRequest, MeResponse, ProjectBrief, SwitchContextRequest, TokenResponse
from app.schemas.user import PasswordChange, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


async def _build_me(user: User, db: AsyncSession) -> MeResponse:
    projects: list[ProjectBrief] = []

    if user.is_system_admin:
        proj_result = await db.execute(select(Project).where(Project.is_enabled.is_(True)))
        for p in proj_result.scalars().all():
            projects.append(ProjectBrief(id=p.id, name=p.name, role="system_admin"))
    else:
        pm_result = await db.execute(
            select(ProjectMember, Project)
            .join(Project, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == user.id, Project.is_enabled.is_(True))
        )
        for member, proj in pm_result.all():
            projects.append(
                ProjectBrief(id=proj.id, name=proj.name, role=member.role.value)
            )

    return MeResponse(user=UserOut.model_validate(user), projects=projects)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled")
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=MeResponse)
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _build_me(user, db)


@router.post("/switch-context", response_model=MeResponse)
async def switch_context(
    body: SwitchContextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.project_id is not None:
        if not await user_can_access_project(user, body.project_id, db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to project")
        user.last_project_id = body.project_id
    await db.flush()
    await db.refresh(user)
    return await _build_me(user, db)


@router.post("/change-password")
async def change_password(
    body: PasswordChange,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.core.security import hash_password

    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password incorrect")
    user.password_hash = hash_password(body.new_password)
    await db.flush()
    return {"ok": True}
