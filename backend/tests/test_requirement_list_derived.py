"""Unit tests for requirement list derived fields."""

from __future__ import annotations

from datetime import date

from app.schemas.requirement import RequirementNodeProgressOut
from app.services.requirement_list_derived import compute_dev_handoff_date


def _node(
    node_key: str,
    *,
    enabled: bool = True,
    planned_schedule_end: date | None = None,
) -> RequirementNodeProgressOut:
    return RequirementNodeProgressOut(
        node_key=node_key,
        label=node_key,
        state="pending",
        role_keys=[],
        enabled=enabled,
        planned_schedule_end=planned_schedule_end,
    )


def test_compute_dev_handoff_date_max_of_enabled_dev_nodes():
    nodes = [
        _node("frontend_dev", planned_schedule_end=date(2024, 11, 10)),
        _node("backend_dev", planned_schedule_end=date(2024, 11, 15)),
        _node("integration", planned_schedule_end=date(2024, 11, 12)),
        _node("req_test", planned_schedule_end=date(2024, 12, 1)),
    ]
    assert compute_dev_handoff_date(nodes) == date(2024, 11, 15)


def test_compute_dev_handoff_date_skips_disabled_nodes():
    nodes = [
        _node("frontend_dev", enabled=False, planned_schedule_end=date(2024, 11, 20)),
        _node("backend_dev", planned_schedule_end=date(2024, 11, 8)),
    ]
    assert compute_dev_handoff_date(nodes) == date(2024, 11, 8)


def test_compute_dev_handoff_date_none_when_no_schedule():
    nodes = [_node("frontend_dev"), _node("backend_dev")]
    assert compute_dev_handoff_date(nodes) is None
