"""Smoke tests for dashboard helpers and schema (no database)."""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import AsyncMock

import pytest

from app.api.v1.dashboard import _build_todo_for_roles, _role_keys
from app.constants.dashboard_todo import (
    MEMBER_FOLLOWER_TODO_STATUS_KEYS,
    TESTER_FIXED_BUG_STATUS_KEY,
    TESTER_TODO_REQUIREMENT_STATUS_KEYS,
)
from app.models.project import ProjectRole
from app.models.project_version import ProjectVersion
from app.schemas.dashboard import (
    ActivePlanBrief,
    DashboardOverview,
    DashboardTodo,
    DashboardWorkbench,
    RequirementTodoBrief,
)
from app.services.dashboard_version import pick_default_version


def _version(
    vid: str,
    *,
    released_at: date | None = None,
    num: int = 1,
    updated_at: datetime | None = None,
) -> ProjectVersion:
    v = ProjectVersion(
        id=vid,
        project_id="p1",
        num=num,
        name=f"v{num}",
        released_at=released_at,
        created_by="u1",
    )
    v.updated_at = updated_at or datetime(2024, 1, 1)
    return v


def test_role_keys_mapping():
    assert _role_keys([], True) == ["system_admin"]
    assert _role_keys([ProjectRole.tester, ProjectRole.product], False) == ["tester", "product"]


@pytest.mark.asyncio
async def test_build_todo_for_roles_returns_all_sections_for_member(monkeypatch):
    from app.api.v1 import dashboard as dashboard_module

    tester_todo = DashboardTodo(
        draft_plans=[
            ActivePlanBrief(
                id="p1",
                name="Plan",
                status="draft",
                case_total=1,
                not_run=1,
                pass_rate=None,
            )
        ],
        active_plans_todo=[],
        fixed_bugs=[],
        not_tested_requirements=[
            RequirementTodoBrief(id="r1", num=1, title="Req", status="developing", version=None)
        ],
        testing_requirements=[],
    )
    dev_todo = DashboardTodo(follower_todo_bugs=[])

    monkeypatch.setattr(
        dashboard_module,
        "_build_todo_tester",
        AsyncMock(return_value=tester_todo),
    )
    monkeypatch.setattr(
        dashboard_module,
        "_build_todo_member",
        AsyncMock(return_value=dev_todo),
    )

    merged = await _build_todo_for_roles(
        "proj-1",
        "user-1",
        {ProjectRole.member},
        is_system_admin=False,
    )
    assert len(merged.draft_plans) == 1
    assert len(merged.not_tested_requirements) == 1
    assert merged.follower_todo_bugs == []
    dashboard_module._build_todo_tester.assert_awaited_once_with("proj-1")
    dashboard_module._build_todo_member.assert_awaited_once_with("proj-1", "user-1")


def test_todo_status_constants():
    assert "pending_confirm" in MEMBER_FOLLOWER_TODO_STATUS_KEYS
    assert "in_progress" in MEMBER_FOLLOWER_TODO_STATUS_KEYS
    assert "suspended" in MEMBER_FOLLOWER_TODO_STATUS_KEYS


def test_unplanned_bug_excluded_status_keys():
    from app.constants.dashboard_todo import UNPLANNED_BUG_EXCLUDED_STATUS_KEYS

    assert "accepted" in UNPLANNED_BUG_EXCLUDED_STATUS_KEYS
    assert "rejected" in UNPLANNED_BUG_EXCLUDED_STATUS_KEYS
    assert "suspended" in UNPLANNED_BUG_EXCLUDED_STATUS_KEYS
    assert "to_requirement" in UNPLANNED_BUG_EXCLUDED_STATUS_KEYS


def test_tester_todo_constants():
    assert TESTER_FIXED_BUG_STATUS_KEY == "fixed"
    assert "developing" in TESTER_TODO_REQUIREMENT_STATUS_KEYS
    from app.constants.dashboard_todo import TESTER_TODO_TESTING_REQUIREMENT_STATUS_KEYS

    assert "testing" in TESTER_TODO_TESTING_REQUIREMENT_STATUS_KEYS
    assert "pending_release" in TESTER_TODO_TESTING_REQUIREMENT_STATUS_KEYS


def test_pick_default_version_prefers_upcoming_including_today():
    today = date(2026, 5, 21)
    past = _version("past", released_at=date(2026, 5, 20), num=1)
    today_v = _version("today", released_at=today, num=2)
    future = _version("future", released_at=date(2026, 6, 1), num=3)
    picked = pick_default_version([past, future, today_v], today=today)
    assert picked is not None
    assert picked.id == "today"


def test_pick_default_version_picks_nearest_future():
    today = date(2026, 5, 21)
    v1 = _version("v1", released_at=date(2026, 6, 10), num=1)
    v2 = _version("v2", released_at=date(2026, 5, 25), num=2)
    picked = pick_default_version([v1, v2], today=today)
    assert picked is not None
    assert picked.id == "v2"


def test_pick_default_version_falls_back_to_latest():
    today = date(2026, 5, 21)
    old = _version("old", released_at=date(2026, 1, 1), num=1, updated_at=datetime(2026, 1, 1))
    latest = _version(
        "latest",
        released_at=date(2026, 4, 1),
        num=5,
        updated_at=datetime(2026, 4, 1),
    )
    picked = pick_default_version([old, latest], today=today)
    assert picked is not None
    assert picked.id == "latest"


def test_pick_default_version_no_released_at_uses_num_and_updated_at():
    today = date(2026, 5, 21)
    a = _version("a", released_at=None, num=1, updated_at=datetime(2026, 1, 1))
    b = _version("b", released_at=None, num=3, updated_at=datetime(2026, 2, 1))
    picked = pick_default_version([a, b], today=today)
    assert picked is not None
    assert picked.id == "b"


def test_dashboard_workbench_schema_roundtrip():
    payload = {
        "summary": {
            "version_count": 2,
            "requirement_count": 5,
            "case_count": 10,
            "bug_count": 3,
        },
        "overview": {
            "version_focus": {
                "version": {"id": "v1", "num": 1, "name": "Sprint"},
                "versions": [{"id": "v1", "num": 1, "name": "Sprint"}],
                "requirements": {"total": 1, "by_status": [{"key": "draft", "label": "草稿", "count": 1}]},
                "bugs": {"total": 0, "by_status": []},
                "plans": {"total": 0, "by_status": []},
            },
            "bug_focus": {
                "by_version_status": {"total": 0, "by_status": [], "versions": [], "cells": []},
                "follower_by_version": {"followers": [], "versions": [], "cells": []},
            },
            "plan_focus": {
                "unfinished_plans": [],
                "execution_chart": {"points": []},
            },
        },
        "todo": {
            "draft_plans": [],
            "active_plans_todo": [],
            "fixed_bugs": [],
            "not_tested_requirements": [],
            "testing_requirements": [],
            "follower_todo_bugs": [],
        },
        "project_roles": ["member", "tester"],
    }
    model = DashboardWorkbench.model_validate(payload)
    assert model.project_roles == ["member", "tester"]
    assert model.summary.bug_count == 3
    assert model.overview.version_focus.version is not None
    assert isinstance(model.todo, DashboardTodo)
    assert isinstance(model.overview, DashboardOverview)
