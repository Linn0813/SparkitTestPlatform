from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.projects import _ensure_not_last_project_admin
from app.models.project import BusinessProjectRole, ProjectMember


def _member(*, is_admin: bool = True, role: BusinessProjectRole = BusinessProjectRole.member) -> ProjectMember:
    return ProjectMember(
        id="mem-1",
        project_id="proj-1",
        user_id="user-1",
        role=role,
        is_project_admin=is_admin,
    )


@pytest.mark.asyncio
async def test_ensure_not_last_project_admin_allows_non_admin():
    db = AsyncMock()
    member = _member(is_admin=False)
    await _ensure_not_last_project_admin(db, "proj-1", member)
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_not_last_project_admin_allows_multiple_admins():
    db = AsyncMock()
    other = _member(is_admin=True)
    other.id = "mem-2"
    other.user_id = "user-2"
    result = MagicMock()
    result.scalars.return_value.all.return_value = [_member(), other]
    db.execute = AsyncMock(return_value=result)
    await _ensure_not_last_project_admin(db, "proj-1", _member())


@pytest.mark.asyncio
async def test_ensure_not_last_project_admin_blocks_last_admin():
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [_member()]
    db.execute = AsyncMock(return_value=result)
    with pytest.raises(HTTPException) as exc:
        await _ensure_not_last_project_admin(db, "proj-1", _member())
    assert exc.value.status_code == 400
    assert "last project admin" in exc.value.detail
