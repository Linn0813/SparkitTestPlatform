"""Smoke tests for dashboard helpers and schema (no database)."""

from __future__ import annotations

from datetime import date, datetime

from app.api.v1.dashboard import _role_key
from app.constants.dashboard_todo import (
    MEMBER_FOLLOWER_TODO_STATUS_KEYS,
    TESTER_FIXED_BUG_STATUS_KEY,
    TESTER_TODO_REQUIREMENT_STATUS_KEYS,
)
from app.models.project import ProjectRole
from app.models.project_version import ProjectVersion
from app.schemas.dashboard import DashboardOverview, DashboardTodo, DashboardWorkbench
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


def test_role_key_mapping():
    assert _role_key(None, True) == "system_admin"
    assert _role_key(None, False) == "member"
    assert _role_key(ProjectRole.tester, False) == "tester"
    assert _role_key(ProjectRole.project_admin, False) == "project_admin"


def test_todo_status_constants():
    assert "pending_confirm" in MEMBER_FOLLOWER_TODO_STATUS_KEYS
    assert "in_progress" in MEMBER_FOLLOWER_TODO_STATUS_KEYS
    assert "suspended" in MEMBER_FOLLOWER_TODO_STATUS_KEYS
    assert TESTER_FIXED_BUG_STATUS_KEY == "fixed"
    assert "not_tested" in TESTER_TODO_REQUIREMENT_STATUS_KEYS
    assert "testing" in TESTER_TODO_REQUIREMENT_STATUS_KEYS


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
                "requirements": {"total": 1, "by_status": [{"key": "not_tested", "label": "未转测", "count": 1}]},
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
        "project_role": "member",
    }
    model = DashboardWorkbench.model_validate(payload)
    assert model.project_role == "member"
    assert model.summary.bug_count == 3
    assert model.overview.version_focus.version is not None
    assert isinstance(model.todo, DashboardTodo)
    assert isinstance(model.overview, DashboardOverview)
