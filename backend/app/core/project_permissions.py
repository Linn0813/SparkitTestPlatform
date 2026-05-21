"""Project-scoped capability checks (member / tester / project_admin)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectMember, ProjectRole
from app.models.user import User

_CATALOG_ROLES = (ProjectRole.member, ProjectRole.tester, ProjectRole.project_admin)
_TESTER_ROLES = (ProjectRole.tester, ProjectRole.project_admin)


async def get_project_role(user: User, project_id: str, db: AsyncSession) -> ProjectRole | None:
    if user.is_system_admin:
        return ProjectRole.project_admin
    result = await db.execute(
        select(ProjectMember.role).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.id,
        )
    )
    row = result.scalar_one_or_none()
    return row


async def user_can_manage_catalog(user: User, project_id: str, db: AsyncSession) -> bool:
    """需求、版本、用例模块：member / tester / project_admin。"""
    if user.is_system_admin:
        return True
    role = await get_project_role(user, project_id, db)
    return role in _CATALOG_ROLES if role else False


async def user_can_manage_cases_and_plans(user: User, project_id: str, db: AsyncSession) -> bool:
    """测试用例、测试计划：tester / project_admin。"""
    if user.is_system_admin:
        return True
    role = await get_project_role(user, project_id, db)
    return role in _TESTER_ROLES if role else False


async def user_can_manage_bugs_full(user: User, project_id: str, db: AsyncSession) -> bool:
    """缺陷完整编辑、新建、删除：tester / project_admin。"""
    return await user_can_manage_cases_and_plans(user, project_id, db)


async def user_can_update_bug_status(user: User, project_id: str, db: AsyncSession) -> bool:
    """缺陷状态、评论：member+。"""
    if user.is_system_admin:
        return True
    role = await get_project_role(user, project_id, db)
    return role is not None


async def user_can_manage_project_settings(user: User, project_id: str, db: AsyncSession) -> bool:
    """项目模板、企微规则、成员管理：project_admin。"""
    if user.is_system_admin:
        return True
    role = await get_project_role(user, project_id, db)
    return role == ProjectRole.project_admin
