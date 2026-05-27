from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.bug import Bug, BugFollowerLink
from app.models.project import BusinessProjectRole, ProjectMember
from app.models.requirement import (
    Requirement,
    RequirementNodeProgress,
    RequirementNodeState,
    RequirementNodeTask,
    RequirementPriority,
    RequirementStatus,
    RequirementType,
)
from app.models.template import RequirementWorkflowNodeDef
from app.models.user import User
from app.services.bug_follower_schedule import _is_schedule_participating, update_bug_follower_schedule
from app.services.links import set_bug_followers
from app.services.member_schedule import (
    _is_fully_scheduled,
    _overlaps_range,
    _skip_unscheduled_for_node_state,
    build_member_schedule,
)


def _task(**kwargs) -> RequirementNodeTask:
    defaults = dict(
        id="task-1",
        requirement_id="req-1",
        node_key="dev",
        title="Android开发",
        role_key="developer",
        assignee_id="user-1",
        estimate_points=2.0,
        scheduled_start=date(2024, 11, 10),
        scheduled_end=date(2024, 11, 12),
        sort=0,
    )
    defaults.update(kwargs)
    return RequirementNodeTask(**defaults)


def _bug_link(**kwargs) -> BugFollowerLink:
    defaults = dict(
        id="link-1",
        bug_id="bug-1",
        user_id="user-1",
        fix_estimate_points=None,
        scheduled_start=None,
        scheduled_end=None,
    )
    defaults.update(kwargs)
    return BugFollowerLink(**defaults)


def _bug(**kwargs) -> Bug:
    defaults = dict(
        id="bug-1",
        project_id="proj-1",
        num=42,
        title="登录失败",
        status_key="new",
        reporter_id="user-1",
        custom_fields={},
    )
    defaults.update(kwargs)
    return Bug(**defaults)


def test_is_fully_scheduled():
    assert _is_fully_scheduled(_task()) is True
    assert _is_fully_scheduled(_task(scheduled_start=None)) is False
    assert _is_fully_scheduled(_task(scheduled_end=None)) is False


def test_overlaps_range():
    t = _task(scheduled_start=date(2024, 11, 10), scheduled_end=date(2024, 11, 12))
    assert _overlaps_range(t, date(2024, 11, 1), date(2024, 11, 30)) is True
    assert _overlaps_range(t, date(2024, 11, 13), date(2024, 11, 20)) is False
    assert _overlaps_range(t, date(2024, 11, 12), date(2024, 11, 15)) is True


def test_skip_unscheduled_for_node_state():
    progress_completed = RequirementNodeProgress(
        requirement_id="req-1",
        node_key="release",
        state=RequirementNodeState.completed,
        enabled=True,
    )
    progress_skipped = RequirementNodeProgress(
        requirement_id="req-1",
        node_key="skip",
        state=RequirementNodeState.skipped,
        enabled=False,
    )
    progress_pending = RequirementNodeProgress(
        requirement_id="req-1",
        node_key="dev",
        state=RequirementNodeState.pending,
        enabled=True,
    )
    assert _skip_unscheduled_for_node_state(progress_completed) is True
    assert _skip_unscheduled_for_node_state(progress_skipped) is True
    assert _skip_unscheduled_for_node_state(progress_pending) is False
    assert _skip_unscheduled_for_node_state(None) is False


def test_is_schedule_participating():
    assert _is_schedule_participating(_bug_link()) is False
    assert _is_schedule_participating(_bug_link(fix_estimate_points=1.0)) is True
    assert _is_schedule_participating(_bug_link(scheduled_start=date(2024, 11, 10))) is True


@pytest.mark.asyncio
async def test_update_bug_follower_schedule():
    link = _bug_link()
    await update_bug_follower_schedule(
        AsyncMock(),
        link,
        fix_estimate_points=2.5,
        scheduled_start=date(2024, 11, 10),
        scheduled_end=date(2024, 11, 12),
        fields_set={"fix_estimate_points", "scheduled_start", "scheduled_end"},
    )
    assert link.fix_estimate_points == 2.5
    assert link.scheduled_start == date(2024, 11, 10)
    assert link.scheduled_end == date(2024, 11, 12)


@pytest.mark.asyncio
async def test_set_bug_followers_preserves_schedule():
    existing = _bug_link(
        id="link-keep",
        user_id="user-1",
        fix_estimate_points=3.0,
        scheduled_start=date(2024, 11, 10),
        scheduled_end=date(2024, 11, 11),
    )
    result = MagicMock()
    result.scalars.return_value.all.return_value = [existing]
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)
    db.delete = AsyncMock()
    db.add = MagicMock()

    await set_bug_followers(db, "bug-1", ["user-1", "user-2"])

    db.delete.assert_not_called()
    assert db.add.call_count == 1
    added = db.add.call_args[0][0]
    assert added.user_id == "user-2"


@pytest.mark.asyncio
async def test_build_member_schedule_buckets():
    user1 = User(id="user-1", email="a@x.com", name="Alice", password_hash="x")
    user2 = User(id="user-2", email="b@x.com", name="Bob", password_hash="x")
    member1 = ProjectMember(
        id="m1",
        project_id="proj-1",
        user_id="user-1",
        role=BusinessProjectRole.member,
        is_project_admin=False,
    )
    member2 = ProjectMember(
        id="m2",
        project_id="proj-1",
        user_id="user-2",
        role=BusinessProjectRole.member,
        is_project_admin=False,
    )
    req = Requirement(
        id="req-1",
        project_id="proj-1",
        num=7,
        title="测试用例插件升级",
        status=RequirementStatus.draft,
        priority=RequirementPriority.p1,
        req_type=RequirementType.feature,
        created_by="user-1",
    )
    scheduled = _task(
        id="t-sched",
        assignee_id="user-1",
        scheduled_start=date(2024, 11, 10),
        scheduled_end=date(2024, 11, 11),
        estimate_points=5.0,
    )
    unscheduled = _task(
        id="t-unsched",
        assignee_id="user-1",
        scheduled_start=None,
        scheduled_end=None,
        title="未填排期",
    )
    out_of_range = _task(
        id="t-out",
        assignee_id="user-2",
        scheduled_start=date(2024, 12, 1),
        scheduled_end=date(2024, 12, 5),
    )
    completed_no_schedule = _task(
        id="t-completed-unsched",
        assignee_id="user-1",
        node_key="release_verify",
        scheduled_start=None,
        scheduled_end=None,
        title="已发版",
    )
    progress_dev = RequirementNodeProgress(
        requirement_id="req-1",
        node_key="dev",
        state=RequirementNodeState.in_progress,
        enabled=True,
    )
    progress_release_completed = RequirementNodeProgress(
        requirement_id="req-1",
        node_key="release_verify",
        state=RequirementNodeState.completed,
        enabled=True,
    )
    progress_out = RequirementNodeProgress(
        requirement_id="req-1",
        node_key="dev",
        state=RequirementNodeState.in_progress,
        enabled=True,
    )
    bug = _bug()
    bug_scheduled = _bug_link(
        id="link-sched",
        user_id="user-1",
        fix_estimate_points=2.0,
        scheduled_start=date(2024, 11, 10),
        scheduled_end=date(2024, 11, 11),
    )
    bug_unscheduled = _bug_link(
        id="link-unsched",
        user_id="user-1",
        fix_estimate_points=1.0,
    )
    bug_empty = _bug_link(id="link-empty", user_id="user-2")
    bug_user2 = _bug_link(
        id="link-u2",
        user_id="user-2",
        fix_estimate_points=4.0,
        scheduled_start=date(2024, 11, 9),
        scheduled_end=date(2024, 11, 10),
    )
    node_def = RequirementWorkflowNodeDef(
        id="def-dev",
        project_id="proj-1",
        node_key="dev",
        label="研发阶段",
        role_keys=["developer"],
        lane_index=0,
        lane_indexes=[0],
        blocks_lane_gate=True,
        sort_in_lane=0,
    )

    members_result = MagicMock()
    members_result.all.return_value = [(member1, user1), (member2, user2)]
    tasks_result = MagicMock()
    tasks_result.all.return_value = [
        (scheduled, req, progress_dev),
        (unscheduled, req, progress_dev),
        (completed_no_schedule, req, progress_release_completed),
        (out_of_range, req, progress_out),
    ]
    bug_links_result = MagicMock()
    bug_links_result.all.return_value = [
        (bug_scheduled, bug),
        (bug_unscheduled, bug),
        (bug_empty, bug),
        (bug_user2, bug),
    ]
    db = AsyncMock()
    call_count = 0

    async def execute_side_effect(_stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return members_result
        if call_count == 2:
            return tasks_result
        return bug_links_result

    db.execute = AsyncMock(side_effect=execute_side_effect)

    load_defs_mock = AsyncMock(return_value=[node_def])
    with patch(
        "app.services.member_schedule.load_project_workflow_defs_for_project",
        load_defs_mock,
    ):
        out = await build_member_schedule(db, "proj-1", date(2024, 11, 8), date(2024, 11, 15))

    assert len(out.members) == 2
    alice = next(m for m in out.members if m.user_id == "user-1")
    assert alice.scheduled_count == 2
    assert alice.unscheduled_count == 2
    assert alice.total_estimate_points == 7.0
    assert alice.scheduled_items[0].node_label == "研发阶段"
    assert alice.scheduled_items[0].requirement_num == 7
    bug_items = [i for i in alice.scheduled_items if i.item_type == "bug"]
    assert len(bug_items) == 1
    assert bug_items[0].bug_num == 42
    bug_unsched_items = [i for i in alice.unscheduled_items if i.item_type == "bug"]
    assert len(bug_unsched_items) == 1
    task_unsched_ids = [i.id for i in alice.unscheduled_items if i.item_type == "requirement_node_task"]
    assert task_unsched_ids == ["t-unsched"]
    assert "t-completed-unsched" not in task_unsched_ids
    bob = next(m for m in out.members if m.user_id == "user-2")
    assert bob.scheduled_count == 1
    assert bob.unscheduled_count == 0
    assert bob.scheduled_items[0].item_type == "bug"
    assert bob.total_estimate_points == 4.0
