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
    _can_start_node,
    derive_requirement_status,
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


def test_derive_status_rejected_sticky():
    req = _make_req(status=RequirementStatus.rejected)
    defs = _default_defs()
    nodes = _nodes({"req_review": RequirementNodeState.pending}, defs=defs)
    assert derive_requirement_status(req, nodes, defs) == RequirementStatus.rejected


def test_derive_status_closed_sticky():
    req = _make_req(status=RequirementStatus.closed)
    defs = _default_defs()
    nodes = _nodes({"frontend_dev": RequirementNodeState.in_progress}, defs=defs)
    assert derive_requirement_status(req, nodes, defs) == RequirementStatus.closed


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
