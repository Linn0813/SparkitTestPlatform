from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.models.requirement import Requirement, RequirementPriority, RequirementStatus, RequirementType
from app.services.requirement_version import CONFLICT_DETAIL, assert_requirement_version


def _make_req(updated_at: datetime) -> Requirement:
    return Requirement(
        id="req-1",
        project_id="proj-1",
        num=1,
        title="Test",
        status=RequirementStatus.draft,
        priority=RequirementPriority.p1,
        req_type=RequirementType.feature,
        created_by="user-1",
        updated_at=updated_at,
    )


def test_assert_version_skips_when_expected_none():
    row = _make_req(datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc))
    assert_requirement_version(row, None)


def test_assert_version_passes_when_match_ignoring_microseconds():
    row = _make_req(datetime(2026, 1, 1, 12, 0, 0, 500000, tzinfo=timezone.utc))
    expected = datetime(2026, 1, 1, 12, 0, 0, 100000, tzinfo=timezone.utc)
    assert_requirement_version(row, expected)


def test_assert_version_passes_naive_and_aware_same_instant():
    aware = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    row = _make_req(datetime(2026, 1, 1, 12, 0, 0))
    assert_requirement_version(row, aware)


def test_assert_version_raises_409_on_mismatch():
    row = _make_req(datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc))
    expected = row.updated_at - timedelta(seconds=1)
    with pytest.raises(HTTPException) as exc:
        assert_requirement_version(row, expected)
    assert exc.value.status_code == 409
    assert exc.value.detail == CONFLICT_DETAIL
