"""Smoke tests for dashboard helpers and schema (no database)."""

from app.api.v1.dashboard import _role_key
from app.constants.dashboard_todo import (
    MEMBER_FOLLOWER_TODO_STATUS_KEYS,
    TESTER_FIXED_BUG_STATUS_KEY,
    TESTER_TODO_REQUIREMENT_STATUS_KEYS,
)
from app.models.project import ProjectRole
from app.schemas.dashboard import DashboardOverview, DashboardTodo, DashboardWorkbench


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
            "bug_overview_chart": {"total": 0, "by_status": [], "versions": [], "cells": []},
            "plan_execution_chart": {"points": []},
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
