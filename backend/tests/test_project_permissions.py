"""Unit tests for project permission helpers (no database)."""

from __future__ import annotations

import pytest

from app.core.project_permissions import roles_include
from app.core.project_roles import member_effective_roles, parse_business_role
from app.models.project import BusinessProjectRole, ProjectMember, ProjectRole


def _member(*, is_admin: bool = False, role: BusinessProjectRole = BusinessProjectRole.member) -> ProjectMember:
    return ProjectMember(
        id="mem-1",
        project_id="proj-1",
        user_id="user-1",
        role=role,
        is_project_admin=is_admin,
    )


def test_member_effective_roles_with_admin():
    roles = member_effective_roles(_member(is_admin=True, role=BusinessProjectRole.tester))
    assert roles == [ProjectRole.tester, ProjectRole.project_admin]


def test_member_effective_roles_business_only():
    roles = member_effective_roles(_member(role=BusinessProjectRole.developer))
    assert roles == [ProjectRole.developer]


def test_roles_include_union():
    roles = [ProjectRole.tester, ProjectRole.developer]
    assert roles_include(roles, ProjectRole.tester)
    assert not roles_include(roles, ProjectRole.product)


def test_parse_business_role_rejects_admin():
    with pytest.raises(ValueError):
        parse_business_role(ProjectRole.project_admin, for_http=False)
