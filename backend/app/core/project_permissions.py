"""Project-scoped capability checks (multi-role union model)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.project_roles import member_effective_roles, roles_include
from app.models.project import ProjectMember, ProjectRole
from app.models.user import User


async def get_project_roles(user: User, project_id: str, db: AsyncSession) -> list[ProjectRole]:
    if user.is_system_admin:
        return list(ProjectRole)
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        return []
    return member_effective_roles(member)


async def user_is_project_member(user: User, project_id: str, db: AsyncSession) -> bool:
    if user.is_system_admin:
        return True
    roles = await get_project_roles(user, project_id, db)
    return len(roles) > 0


async def user_can_manage_project_settings(user: User, project_id: str, db: AsyncSession) -> bool:
    if user.is_system_admin:
        return True
    roles = await get_project_roles(user, project_id, db)
    return roles_include(roles, ProjectRole.project_admin)


async def user_can_manage_requirements(user: User, project_id: str, db: AsyncSession) -> bool:
    """需求、版本、用例模块：任意项目角色。"""
    return await user_is_project_member(user, project_id, db)


async def user_can_manage_catalog(user: User, project_id: str, db: AsyncSession) -> bool:
    return await user_can_manage_requirements(user, project_id, db)


async def user_can_manage_cases_and_plans(user: User, project_id: str, db: AsyncSession) -> bool:
    """测试用例、测试计划：tester。"""
    if user.is_system_admin:
        return True
    roles = await get_project_roles(user, project_id, db)
    return roles_include(roles, ProjectRole.tester)


async def user_can_manage_bugs_full(user: User, project_id: str, db: AsyncSession) -> bool:
    """缺陷完整编辑、新建、删除：tester / product。"""
    if user.is_system_admin:
        return True
    roles = await get_project_roles(user, project_id, db)
    return roles_include(roles, ProjectRole.tester, ProjectRole.product)


async def user_can_update_bug_status(user: User, project_id: str, db: AsyncSession) -> bool:
    """缺陷状态、评论：developer / tester / product。"""
    if user.is_system_admin:
        return True
    roles = await get_project_roles(user, project_id, db)
    return roles_include(
        roles,
        ProjectRole.developer,
        ProjectRole.tester,
        ProjectRole.product,
    )


async def user_can_update_bug_followers(user: User, project_id: str, db: AsyncSession) -> bool:
    """缺陷跟进人：developer / tester / product（与改状态相同）。"""
    return await user_can_update_bug_status(user, project_id, db)


async def user_can_access_bugs_module(user: User, project_id: str, db: AsyncSession) -> bool:
    if user.is_system_admin:
        return True
    roles = await get_project_roles(user, project_id, db)
    return roles_include(
        roles,
        ProjectRole.tester,
        ProjectRole.product,
        ProjectRole.developer,
    )
