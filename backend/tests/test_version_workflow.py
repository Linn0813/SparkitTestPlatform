from __future__ import annotations

from datetime import date

import pytest

from app.models.project_version import ProjectVersion
from app.models.version_workflow import VersionNodeProgress, VersionNodeState, VersionStatus
from app.services.version_workflow import (
    VersionWorkflowError,
    compute_version_status,
    complete_version_node,
    reopen_version_node,
)


def _nodes(states: dict[str, str]) -> dict[str, VersionNodeProgress]:
    result: dict[str, VersionNodeProgress] = {}
    for key, state in states.items():
        result[key] = VersionNodeProgress(
            version_id="ver-1",
            node_key=key,
            state=state,
        )
    return result


def test_compute_status_planning_default():
    nodes = _nodes({k: VersionNodeState.pending.value for k in ("planning", "development")})
    assert compute_version_status(nodes) == VersionStatus.planning


def test_compute_status_developing():
    nodes = _nodes(
        {
            "planning": VersionNodeState.completed.value,
            "development": VersionNodeState.pending.value,
        }
    )
    assert compute_version_status(nodes) == VersionStatus.developing


def test_compute_status_releasing():
    nodes = _nodes(
        {
            "planning": VersionNodeState.completed.value,
            "development": VersionNodeState.completed.value,
            "release_verification": VersionNodeState.pending.value,
        }
    )
    assert compute_version_status(nodes) == VersionStatus.releasing


def test_compute_status_reviewing():
    nodes = _nodes(
        {
            "planning": VersionNodeState.completed.value,
            "development": VersionNodeState.completed.value,
            "release_verification": VersionNodeState.completed.value,
            "gp_review": VersionNodeState.pending.value,
        }
    )
    assert compute_version_status(nodes) == VersionStatus.reviewing


def test_compute_status_ended():
    nodes = _nodes({"live": VersionNodeState.completed.value})
    assert compute_version_status(nodes) == VersionStatus.ended


@pytest.mark.asyncio
async def test_complete_node_sets_released_at_on_live():
    version = ProjectVersion(
        id="ver-1",
        project_id="proj-1",
        num=1,
        name="v1.0",
        created_by="u1",
    )
    db_nodes: dict[str, VersionNodeProgress] = {}
    for key in (
        "planning",
        "development",
        "release_verification",
        "gp_review",
        "as_review",
        "website_link",
        "live",
    ):
        db_nodes[key] = VersionNodeProgress(
            version_id="ver-1",
            node_key=key,
            state=VersionNodeState.pending.value,
        )
    for key in ("planning", "development", "release_verification", "gp_review", "as_review", "website_link"):
        db_nodes[key].state = VersionNodeState.completed.value

    class FakeSession:
        async def flush(self):
            pass

    async def fake_load(db, version_id):
        return db_nodes

    import app.services.version_workflow as wf

    original = wf.load_version_nodes
    wf.load_version_nodes = fake_load
    try:
        await complete_version_node(FakeSession(), version, "live", "op-1")
    finally:
        wf.load_version_nodes = original

    assert version.released_at == date.today()
    assert version.status == VersionStatus.ended.value
    assert db_nodes["live"].state == VersionNodeState.completed.value


@pytest.mark.asyncio
async def test_complete_development_requires_planning():
    version = ProjectVersion(
        id="ver-1",
        project_id="proj-1",
        num=1,
        name="v1.0",
        created_by="u1",
    )
    db_nodes = {
        "planning": VersionNodeProgress(
            version_id="ver-1", node_key="planning", state=VersionNodeState.pending.value
        ),
        "development": VersionNodeProgress(
            version_id="ver-1", node_key="development", state=VersionNodeState.pending.value
        ),
    }

    class FakeSession:
        async def flush(self):
            pass

    import app.services.version_workflow as wf

    async def fake_load(db, vid):
        return db_nodes

    original = wf.load_version_nodes
    wf.load_version_nodes = fake_load
    try:
        with pytest.raises(VersionWorkflowError, match="版本规划"):
            await complete_version_node(FakeSession(), version, "development", "op-1")
    finally:
        wf.load_version_nodes = original


@pytest.mark.asyncio
async def test_reopen_gp_only_reopens_live_not_siblings():
    version = ProjectVersion(
        id="ver-1",
        project_id="proj-1",
        num=1,
        name="v1.0",
        status=VersionStatus.ended.value,
        created_by="u1",
    )
    keys = ("planning", "development", "release_verification", "gp_review", "as_review", "website_link", "live")
    db_nodes = {
        k: VersionNodeProgress(
            version_id="ver-1",
            node_key=k,
            state=VersionNodeState.completed.value,
        )
        for k in keys
    }

    class FakeSession:
        async def flush(self):
            pass

    import app.services.version_workflow as wf

    async def fake_load(db, vid):
        return db_nodes

    original = wf.load_version_nodes
    wf.load_version_nodes = fake_load
    try:
        await reopen_version_node(FakeSession(), version, "gp_review")
    finally:
        wf.load_version_nodes = original

    assert db_nodes["gp_review"].state == VersionNodeState.pending.value
    assert db_nodes["as_review"].state == VersionNodeState.completed.value
    assert db_nodes["website_link"].state == VersionNodeState.completed.value
    assert db_nodes["live"].state == VersionNodeState.pending.value
    assert version.status == VersionStatus.reviewing.value
