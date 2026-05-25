"""Helpers for project member role storage and checks."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.models.project import BusinessProjectRole, ProjectMember, ProjectRole

BUSINESS_ROLES = (
    ProjectRole.member,
    ProjectRole.tester,
    ProjectRole.product,
    ProjectRole.developer,
)

_BUSINESS_ROLE_VALUES = {r.value for r in BUSINESS_ROLES}


def parse_business_role(value: str | ProjectRole | BusinessProjectRole, *, for_http: bool = True) -> ProjectRole:
    if isinstance(value, BusinessProjectRole):
        return ProjectRole(value.value)
    val = value.value if isinstance(value, ProjectRole) else str(value).strip()
    if val == ProjectRole.project_admin.value:
        msg = "project_admin must use is_project_admin field"
        if for_http:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
        raise ValueError(msg)
    if val not in _BUSINESS_ROLE_VALUES:
        msg = f"Invalid role: {val}"
        if for_http:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
        raise ValueError(msg)
    return ProjectRole(val)


def roles_include(roles: list[ProjectRole], *keys: ProjectRole) -> bool:
    role_set = set(roles)
    return any(k in role_set for k in keys)


def member_is_project_admin(member: ProjectMember) -> bool:
    return bool(member.is_project_admin)


def member_business_role(member: ProjectMember) -> ProjectRole:
    raw = member.role.value if hasattr(member.role, "value") else str(member.role)
    return ProjectRole(raw)


def member_effective_roles(member: ProjectMember) -> list[ProjectRole]:
    roles = [member_business_role(member)]
    if member_is_project_admin(member):
        roles.append(ProjectRole.project_admin)
    return roles
