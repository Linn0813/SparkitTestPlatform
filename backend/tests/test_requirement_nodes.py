from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.requirement import (
    Requirement,
    RequirementNodeProgress,
    RequirementNodeState,
    RequirementPriority,
    RequirementStatus,
    RequirementType,
)
from app.models.template import RequirementWorkflowNodeDef
from app.services.requirement_nodes import (
    RequirementNodeError,
    _can_complete_node,
    _can_start_node,
    apply_node_action,
    auto_start_ready_nodes,
    derive_requirement_status,
    sync_requirement_status_from_workflow,
    update_requirement_enabled_nodes,
)
from app.services.requirement_status_rules import default_status_rule_likes
from app.services.requirement_workflow import assert_workflow_node_deletable
from app.services.requirement_workflow_defaults import DEFAULT_REQUIREMENT_WORKFLOW_NODES


def _default_defs(extra: list[dict] | None = None) -> list[RequirementWorkflowNodeDef]:
    rows = [
        RequirementWorkflowNodeDef(id=f"def-{item['node_key']}", project_id="proj-1", **item)
        for item in DEFAULT_REQUIREMENT_WORKFLOW_NODES
    ]
    if extra:
        for item in extra:
            rows.append(
                RequirementWorkflowNodeDef(
                    id=item.get("id", f"def-{item['node_key']}"),
                    project_id="proj-1",
                    **{k: v for k, v in item.items() if k != "id"},
                )
            )
    return rows


def _make_req(**kwargs) -> Requirement:
    defaults = dict(
        id="req-1",
        project_id="proj-1",
        num=1,
        title="Test",
        status=RequirementStatus.draft,
        priority=RequirementPriority.p1,
        req_type=RequirementType.feature,
        created_by="user-1",
    )
    defaults.update(kwargs)
    return Requirement(**defaults)


def _nodes(
    states: dict[str, RequirementNodeState] | None = None,
    *,
    enabled: dict[str, bool] | None = None,
    defs: list[RequirementWorkflowNodeDef] | None = None,
) -> dict[str, RequirementNodeProgress]:
    states = states or {}
    enabled_map = enabled or {}
    defs = defs or _default_defs()
    result: dict[str, RequirementNodeProgress] = {}
    for d in defs:
        key = d.node_key
        en = enabled_map.get(key, True)
        state = states.get(key, RequirementNodeState.pending)
        if not en and key not in states:
            state = RequirementNodeState.skipped
        result[key] = RequirementNodeProgress(
            requirement_id="req-1",
            node_key=key,
            state=state,
            enabled=en,
        )
    return result


def test_derive_status_draft_by_default():
    req = _make_req()
    defs = _default_defs()
    assert derive_requirement_status(req, _nodes(defs=defs), defs) == RequirementStatus.draft


def test_derive_status_designing():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.in_progress,
        },
        defs=defs,
    )
    assert derive_requirement_status(req, nodes, defs) == RequirementStatus.designing


def test_derive_status_draft_when_prd_and_design_incomplete():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.pending,
            "req_design": RequirementNodeState.in_progress,
        },
        defs=defs,
    )
    assert derive_requirement_status(req, nodes, defs) == RequirementStatus.draft


def test_derive_status_draft_when_design_done_prd_not():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.in_progress,
            "req_design": RequirementNodeState.completed,
        },
        defs=defs,
    )
    assert derive_requirement_status(req, nodes, defs) == RequirementStatus.draft


def test_derive_status_pending_review_when_phase1_done():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.completed,
        },
        defs=defs,
    )
    assert derive_requirement_status(req, nodes, defs) == RequirementStatus.pending_review


def test_derive_status_developing_parallel_dev():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.completed,
            "req_review": RequirementNodeState.completed,
            "frontend_dev": RequirementNodeState.in_progress,
            "backend_dev": RequirementNodeState.pending,
        },
        defs=defs,
    )
    assert derive_requirement_status(req, nodes, defs) == RequirementStatus.developing


def test_derive_status_developing_on_integration():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.completed,
            "req_review": RequirementNodeState.completed,
            "frontend_dev": RequirementNodeState.completed,
            "backend_dev": RequirementNodeState.completed,
            "integration": RequirementNodeState.in_progress,
        },
        defs=defs,
    )
    assert derive_requirement_status(req, nodes, defs) == RequirementStatus.developing


def test_derive_status_testing_after_dev_and_integration_done():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.completed,
            "req_review": RequirementNodeState.completed,
            "frontend_dev": RequirementNodeState.completed,
            "backend_dev": RequirementNodeState.completed,
            "integration": RequirementNodeState.completed,
            "req_test": RequirementNodeState.pending,
        },
        defs=defs,
    )
    assert derive_requirement_status(req, nodes, defs) == RequirementStatus.testing


def test_derive_status_pending_release_on_released_lane():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.completed,
            "req_review": RequirementNodeState.completed,
            "frontend_dev": RequirementNodeState.completed,
            "backend_dev": RequirementNodeState.completed,
            "integration": RequirementNodeState.completed,
            "req_test": RequirementNodeState.completed,
            "product_experience": RequirementNodeState.completed,
            "ui_restoration": RequirementNodeState.completed,
            "released": RequirementNodeState.in_progress,
        },
        defs=defs,
    )
    assert derive_requirement_status(req, nodes, defs) == RequirementStatus.pending_release


def test_derive_status_testing_phase5():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.completed,
            "req_review": RequirementNodeState.completed,
            "frontend_dev": RequirementNodeState.completed,
            "backend_dev": RequirementNodeState.completed,
            "integration": RequirementNodeState.completed,
            "req_test": RequirementNodeState.in_progress,
        },
        defs=defs,
    )
    assert derive_requirement_status(req, nodes, defs) == RequirementStatus.testing


def test_derive_status_released():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes({"released": RequirementNodeState.completed}, defs=defs)
    assert derive_requirement_status(req, nodes, defs) == RequirementStatus.released


def test_derive_status_closed_sticky():
    req = _make_req(status=RequirementStatus.closed)
    defs = _default_defs()
    nodes = _nodes({"frontend_dev": RequirementNodeState.in_progress}, defs=defs)
    assert derive_requirement_status(req, nodes, defs) == RequirementStatus.closed


def test_derive_status_pending_review_when_review_lane_active():
    """评审节点未完成时应为待评审（打回后不再使用 rejected 状态）。"""
    req = _make_req(status=RequirementStatus.draft)
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.completed,
            "req_review": RequirementNodeState.pending,
        },
        defs=defs,
    )
    assert derive_requirement_status(req, nodes, defs) == RequirementStatus.pending_review


def test_derive_status_developing_when_integration_pending_not_pending_release():
    """联调未开始、发版未开始时不应为待发版（旧规则遗留场景）。"""
    req = _make_req(status=RequirementStatus.pending_release)
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.completed,
            "req_review": RequirementNodeState.completed,
            "frontend_dev": RequirementNodeState.completed,
            "backend_dev": RequirementNodeState.completed,
            "integration": RequirementNodeState.pending,
            "released": RequirementNodeState.pending,
        },
        defs=defs,
    )
    assert derive_requirement_status(req, nodes, defs) == RequirementStatus.developing


@pytest.mark.asyncio
async def test_sync_requirement_status_writes_back():
    req = _make_req(status=RequirementStatus.pending_release)
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.completed,
            "req_review": RequirementNodeState.completed,
            "frontend_dev": RequirementNodeState.completed,
            "backend_dev": RequirementNodeState.completed,
            "integration": RequirementNodeState.pending,
        },
        defs=defs,
    )
    db = AsyncMock()
    with patch(
        "app.services.requirement_nodes.load_status_rules_for_derive",
        new=AsyncMock(return_value=default_status_rule_likes()),
    ), patch(
        "app.services.requirement_nodes.load_node_map",
        new=AsyncMock(return_value=nodes),
    ), patch(
        "app.services.requirement_workflow.load_project_workflow_defs",
        new=AsyncMock(return_value=defs),
    ):
        new_status, changed = await sync_requirement_status_from_workflow(
            db, req, actor_id="user-1", log_activity=False
        )
    assert changed is True
    assert new_status == RequirementStatus.developing
    assert req.status == RequirementStatus.developing


def test_gate_review_requires_phase1():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes(defs=defs)
    with pytest.raises(RequirementNodeError, match="上一阶段"):
        _can_start_node(req, nodes, defs, "req_review")


def test_gate_integration_requires_both_dev_when_enabled():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes(
        {
            "req_review": RequirementNodeState.completed,
            "frontend_dev": RequirementNodeState.completed,
            "backend_dev": RequirementNodeState.pending,
        },
        defs=defs,
    )
    with pytest.raises(RequirementNodeError, match="上一阶段"):
        _can_start_node(req, nodes, defs, "integration")


def test_disabled_node_skips_gate():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.skipped,
            "req_review": RequirementNodeState.pending,
        },
        enabled={"req_design": False},
        defs=defs,
    )
    _can_start_node(req, nodes, defs, "req_review")


def test_whole_lane_disabled_auto_skips():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.skipped,
            "req_design": RequirementNodeState.skipped,
            "req_review": RequirementNodeState.pending,
        },
        enabled={"prd_output": False, "req_design": False},
        defs=defs,
    )
    _can_start_node(req, nodes, defs, "req_review")


def test_custom_node_in_lane_requires_previous_lane():
    req = _make_req()
    defs = _default_defs(
        [
            {
                "node_key": "custom_case_design",
                "label": "用例设计",
                "role_keys": ["qa"],
                "lane_index": 1,
                "sort_in_lane": 1,
            }
        ]
    )
    nodes = _nodes(defs=defs)
    with pytest.raises(RequirementNodeError, match="上一阶段"):
        _can_start_node(req, nodes, defs, "custom_case_design")

    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.completed,
            "req_review": RequirementNodeState.completed,
            "custom_case_design": RequirementNodeState.pending,
        },
        defs=defs,
    )
    _can_start_node(req, nodes, defs, "custom_case_design")


def test_disabled_frontend_dev_allows_integration_when_backend_done():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.completed,
            "req_review": RequirementNodeState.completed,
            "frontend_dev": RequirementNodeState.skipped,
            "backend_dev": RequirementNodeState.completed,
            "integration": RequirementNodeState.pending,
        },
        enabled={"frontend_dev": False},
        defs=defs,
    )
    _can_start_node(req, nodes, defs, "integration")


@pytest.mark.asyncio
async def test_released_can_be_disabled():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes(defs=defs)
    db = AsyncMock()
    with patch(
        "app.services.requirement_nodes.load_status_rules_for_derive",
        new=AsyncMock(return_value=default_status_rule_likes()),
    ):
        await update_requirement_enabled_nodes(
            db,
            req,
            nodes,
            defs,
            {"released": False},
            actor_id="user-1",
        )
    assert nodes["released"].enabled is False
    assert nodes["released"].state == RequirementNodeState.skipped


@pytest.mark.asyncio
async def test_assert_workflow_node_deletable_blocks_in_progress():
    result = MagicMock()
    result.scalar.return_value = 1
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    with pytest.raises(ValueError, match="进行中"):
        await assert_workflow_node_deletable(db, "req_review")


@pytest.mark.asyncio
async def test_assert_workflow_node_deletable_allows_when_idle():
    result = MagicMock()
    result.scalar.return_value = 0
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    await assert_workflow_node_deletable(db, "prd_output")


def _defs_with_case_design_parallel() -> list[RequirementWorkflowNodeDef]:
    """Lane2 dev + case design (non-blocking); lane3 integration."""
    return _default_defs(
        extra=[
            {
                "node_key": "case_design",
                "label": "用例设计",
                "role_keys": ["qa"],
                "lane_index": 2,
                "lane_indexes": [2, 3],
                "blocks_lane_gate": False,
                "sort_in_lane": 2,
            }
        ]
    )


def test_integration_starts_when_non_blocking_case_design_incomplete():
    req = _make_req()
    defs = _defs_with_case_design_parallel()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.completed,
            "req_review": RequirementNodeState.completed,
            "frontend_dev": RequirementNodeState.completed,
            "backend_dev": RequirementNodeState.completed,
            "case_design": RequirementNodeState.in_progress,
            "integration": RequirementNodeState.pending,
        },
        defs=defs,
    )
    _can_start_node(req, nodes, defs, "integration")


def test_case_design_and_frontend_dev_start_after_review():
    req = _make_req()
    defs = _defs_with_case_design_parallel()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.completed,
            "req_review": RequirementNodeState.completed,
            "frontend_dev": RequirementNodeState.pending,
            "case_design": RequirementNodeState.pending,
        },
        defs=defs,
    )
    _can_start_node(req, nodes, defs, "frontend_dev")
    _can_start_node(req, nodes, defs, "case_design")


def test_auto_start_ready_nodes_after_dev_complete():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.completed,
            "req_review": RequirementNodeState.completed,
            "frontend_dev": RequirementNodeState.completed,
            "backend_dev": RequirementNodeState.completed,
            "integration": RequirementNodeState.pending,
        },
        defs=defs,
    )
    started = auto_start_ready_nodes(req, nodes, defs)
    assert "integration" in started
    assert nodes["integration"].state == RequirementNodeState.in_progress


def test_auto_start_does_not_start_when_gate_blocked():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes(defs=defs)
    started = auto_start_ready_nodes(req, nodes, defs)
    assert "req_review" not in started
    assert nodes["req_review"].state == RequirementNodeState.pending


@pytest.mark.asyncio
async def test_apply_complete_from_pending_auto_starts():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.completed,
            "req_review": RequirementNodeState.pending,
        },
        defs=defs,
    )
    db = AsyncMock()
    with patch(
        "app.services.requirement_nodes.load_status_rules_for_derive",
        new=AsyncMock(return_value=default_status_rule_likes()),
    ), patch("app.services.requirement_nodes.log_requirement_activity", new=AsyncMock()):
        await apply_node_action(
            db,
            req,
            nodes,
            defs,
            node_key="req_review",
            action="complete",
            actor_id="user-1",
        )
    assert nodes["req_review"].state == RequirementNodeState.completed


def test_complete_in_progress_blocked_when_upstream_reopened():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.pending,
            "req_design": RequirementNodeState.completed,
            "req_review": RequirementNodeState.in_progress,
        },
        defs=defs,
    )
    with pytest.raises(RequirementNodeError, match="上一阶段"):
        _can_complete_node(nodes, defs, "req_review")


@pytest.mark.asyncio
async def test_apply_complete_in_progress_succeeds():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.completed,
            "req_review": RequirementNodeState.in_progress,
        },
        defs=defs,
    )
    db = AsyncMock()
    with patch(
        "app.services.requirement_nodes.load_status_rules_for_derive",
        new=AsyncMock(return_value=default_status_rule_likes()),
    ), patch("app.services.requirement_nodes.log_requirement_activity", new=AsyncMock()):
        await apply_node_action(
            db,
            req,
            nodes,
            defs,
            node_key="req_review",
            action="complete",
            actor_id="user-1",
        )
    assert nodes["req_review"].state == RequirementNodeState.completed


@pytest.mark.asyncio
async def test_complete_backend_dev_auto_starts_integration():
    req = _make_req(status=RequirementStatus.developing)
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.completed,
            "req_review": RequirementNodeState.completed,
            "frontend_dev": RequirementNodeState.completed,
            "backend_dev": RequirementNodeState.in_progress,
            "integration": RequirementNodeState.pending,
        },
        defs=defs,
    )
    db = AsyncMock()
    with patch(
        "app.services.requirement_nodes.load_status_rules_for_derive",
        new=AsyncMock(return_value=default_status_rule_likes()),
    ), patch("app.services.requirement_nodes.log_requirement_activity", new=AsyncMock()):
        await apply_node_action(
            db,
            req,
            nodes,
            defs,
            node_key="backend_dev",
            action="complete",
            actor_id="user-1",
        )
    assert nodes["backend_dev"].state == RequirementNodeState.completed
    assert nodes["integration"].state == RequirementNodeState.in_progress


@pytest.mark.asyncio
async def test_complete_req_test_auto_starts_released():
    req = _make_req(status=RequirementStatus.pending_release)
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.completed,
            "req_review": RequirementNodeState.completed,
            "frontend_dev": RequirementNodeState.completed,
            "backend_dev": RequirementNodeState.completed,
            "integration": RequirementNodeState.completed,
            "req_test": RequirementNodeState.in_progress,
            "product_experience": RequirementNodeState.completed,
            "ui_restoration": RequirementNodeState.completed,
            "released": RequirementNodeState.pending,
        },
        defs=defs,
    )
    db = AsyncMock()
    with patch(
        "app.services.requirement_nodes.load_status_rules_for_derive",
        new=AsyncMock(return_value=default_status_rule_likes()),
    ), patch("app.services.requirement_nodes.log_requirement_activity", new=AsyncMock()):
        await apply_node_action(
            db,
            req,
            nodes,
            defs,
            node_key="req_test",
            action="complete",
            actor_id="user-1",
        )
    assert nodes["req_test"].state == RequirementNodeState.completed
    assert nodes["released"].state == RequirementNodeState.in_progress


@pytest.mark.asyncio
async def test_disable_frontend_auto_starts_integration():
    req = _make_req(status=RequirementStatus.developing)
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.completed,
            "req_review": RequirementNodeState.completed,
            "frontend_dev": RequirementNodeState.completed,
            "backend_dev": RequirementNodeState.completed,
            "integration": RequirementNodeState.pending,
        },
        defs=defs,
    )
    db = AsyncMock()
    with patch(
        "app.services.requirement_nodes.load_status_rules_for_derive",
        new=AsyncMock(return_value=default_status_rule_likes()),
    ):
        await update_requirement_enabled_nodes(
            db,
            req,
            nodes,
            defs,
            {"frontend_dev": False},
            actor_id="user-1",
        )
    assert nodes["frontend_dev"].enabled is False
    assert nodes["frontend_dev"].state == RequirementNodeState.skipped
    assert nodes["integration"].state == RequirementNodeState.in_progress


@pytest.mark.asyncio
async def test_disable_dev_node_reverts_downstream_in_progress():
    req = _make_req(status=RequirementStatus.developing)
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.completed,
            "req_review": RequirementNodeState.completed,
            "frontend_dev": RequirementNodeState.in_progress,
            "backend_dev": RequirementNodeState.completed,
            "integration": RequirementNodeState.in_progress,
        },
        defs=defs,
    )
    db = AsyncMock()
    with patch(
        "app.services.requirement_nodes.load_status_rules_for_derive",
        new=AsyncMock(return_value=default_status_rule_likes()),
    ):
        await update_requirement_enabled_nodes(
            db,
            req,
            nodes,
            defs,
            {"backend_dev": False},
            actor_id="user-1",
        )
    assert nodes["integration"].state == RequirementNodeState.pending


def test_derive_designing_when_prd_disabled():
    req = _make_req()
    defs = _default_defs()
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.skipped,
            "req_design": RequirementNodeState.in_progress,
        },
        enabled={"prd_output": False},
        defs=defs,
    )
    status = derive_requirement_status(req, nodes, defs, rules=default_status_rule_likes())
    assert status == RequirementStatus.designing


def test_sync_role_assignees_sets_legacy_id_fields():
    from app.api.v1.requirements import _sync_role_id_fields_from_assignees

    data: dict = {"role_assignee_ids": {"pm": ["user-pm"], "qa": ["user-qa-1", "user-qa-2"]}}
    _sync_role_id_fields_from_assignees(data)
    assert data["pm_id"] == "user-pm"
    assert data["qa_id"] == "user-qa-1"


def test_resolve_node_enabled_from_map_and_req_type():
    from app.models.requirement import RequirementType
    from app.services.requirement_workflow import resolve_node_enabled

    assert resolve_node_enabled("req_design", RequirementType.tech_optimization, None) is False
    assert resolve_node_enabled("prd_output", RequirementType.tech_optimization, None) is True
    assert (
        resolve_node_enabled("frontend_dev", RequirementType.feature, {"frontend_dev": False})
        is False
    )
    assert (
        resolve_node_enabled("frontend_dev", RequirementType.feature, {"frontend_dev": True})
        is True
    )


@pytest.mark.asyncio
async def test_init_progress_respects_enabled_map():
    from app.models.requirement import Requirement
    from app.services.requirement_workflow import init_requirement_progress_from_defs

    req = Requirement(
        id="req-1",
        project_id="proj-1",
        num=1,
        title="T",
        status=RequirementStatus.draft,
        priority=RequirementPriority.p1,
        req_type=RequirementType.feature,
        created_by="user-1",
    )
    defs = _default_defs()
    db = AsyncMock()
    progress_rows: list[RequirementNodeProgress] = []

    def add(row):
        progress_rows.append(row)

    db.add = MagicMock(side_effect=add)
    db.flush = AsyncMock()

    await init_requirement_progress_from_defs(
        db,
        req,
        defs,
        enabled_map={"frontend_dev": False, "backend_dev": True, "released": True},
    )
    by_key = {r.node_key: r for r in progress_rows}
    assert by_key["frontend_dev"].enabled is False
    assert by_key["frontend_dev"].state == RequirementNodeState.skipped
    assert by_key["backend_dev"].enabled is True
    assert by_key["backend_dev"].state == RequirementNodeState.pending


def test_lane_without_blocking_nodes_auto_passes_gate():
    req = _make_req()
    defs = _default_defs(
        extra=[
            {
                "node_key": "observe_only",
                "label": "观察项",
                "role_keys": ["pm"],
                "lane_index": 1,
                "lane_indexes": [1],
                "blocks_lane_gate": False,
                "sort_in_lane": 9,
            }
        ]
    )
    nodes = _nodes(
        {
            "prd_output": RequirementNodeState.completed,
            "req_design": RequirementNodeState.completed,
            "observe_only": RequirementNodeState.in_progress,
            "req_review": RequirementNodeState.pending,
        },
        defs=defs,
    )
    _can_start_node(req, nodes, defs, "req_review")
