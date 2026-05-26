from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.project_permissions import (
    user_can_manage_bugs_full,
    user_can_manage_catalog,
    user_can_manage_cases_and_plans,
    user_can_manage_project_settings,
    user_is_project_member,
)
from app.core.security import decode_access_token
from app.models.project import Project, ProjectMember
from app.models.user import User

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or disabled")
    return user


async def require_system_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_system_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System admin required")
    return user


async def require_project_access(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not await user_is_project_member(user, project_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No project access")
    return user


async def require_project_admin(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not await user_can_manage_project_settings(user, project_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project admin required")
    return user


@dataclass
class ProjectContext:
    user: User
    project_id: str


async def _resolve_project(project_id: str, db: AsyncSession) -> Project:
    project = await db.get(Project, project_id)
    if not project or not project.is_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


async def require_project_context(
    x_project_id: Optional[str] = Header(default=None, alias="X-Project-Id"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectContext:
    if not x_project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Project-Id header required")
    await _resolve_project(x_project_id, db)
    await require_project_access(x_project_id, user, db)
    return ProjectContext(user=user, project_id=x_project_id)


async def require_project_context_tester(
    x_project_id: Optional[str] = Header(default=None, alias="X-Project-Id"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectContext:
    return await require_project_context_cases_plans(x_project_id, user, db)


async def require_project_context_admin(
    x_project_id: Optional[str] = Header(default=None, alias="X-Project-Id"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectContext:
    if not x_project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Project-Id header required")
    await _resolve_project(x_project_id, db)
    if not await user_can_manage_project_settings(user, x_project_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project admin required")
    return ProjectContext(user=user, project_id=x_project_id)


async def require_project_context_catalog(
    x_project_id: Optional[str] = Header(default=None, alias="X-Project-Id"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectContext:
    """需求、版本、用例模块写操作：任意项目角色。"""
    if not x_project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Project-Id header required")
    await _resolve_project(x_project_id, db)
    if not await user_can_manage_catalog(user, x_project_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient project role")
    return ProjectContext(user=user, project_id=x_project_id)


async def require_project_context_cases_plans(
    x_project_id: Optional[str] = Header(default=None, alias="X-Project-Id"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectContext:
    """测试用例、测试计划写操作：tester。"""
    if not x_project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Project-Id header required")
    await _resolve_project(x_project_id, db)
    if not await user_can_manage_cases_and_plans(user, x_project_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient project role")
    return ProjectContext(user=user, project_id=x_project_id)


async def require_project_context_bugs_full(
    x_project_id: Optional[str] = Header(default=None, alias="X-Project-Id"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectContext:
    """缺陷完整写操作：tester / product（与 user_can_manage_bugs_full 一致）。"""
    if not x_project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Project-Id header required")
    await _resolve_project(x_project_id, db)
    if not await user_can_manage_bugs_full(user, x_project_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient project role")
    return ProjectContext(user=user, project_id=x_project_id)


async def user_can_full_edit_project(user: User, project_id: str, db: AsyncSession) -> bool:
    return await user_can_manage_bugs_full(user, project_id, db)


async def user_can_access_project(user: User, project_id: str, db: AsyncSession) -> bool:
    if user.is_system_admin:
        project = await db.get(Project, project_id)
        return project is not None and project.is_enabled
    result = await db.execute(
        select(ProjectMember)
        .join(Project, ProjectMember.project_id == Project.id)
        .where(ProjectMember.project_id == project_id, ProjectMember.user_id == user.id, Project.is_enabled.is_(True))
    )
    return result.scalar_one_or_none() is not None
