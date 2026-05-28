from __future__ import annotations

from datetime import date

import pytest

from app.models.project_version import ProjectVersion
from app.models.template import VersionWorkflowNodeDef
from app.models.version_workflow import VersionNodeProgress, VersionNodeState, VersionStatus
from app.services.version_workflow import (
    VersionWorkflowError,
    assert_version_workflow_node_deletable,
    auto_start_ready_version_nodes,
    compute_version_status,
    complete_version_node,
    ensure_version_workflow_nodes_started,
    reopen_version_node,
    sync_version_progress_for_new_def,
)
from app.services.version_workflow_defaults import DEFAULT_APP_RELEASE_WORKFLOW_NODES


def _nodes(states: dict[str, str]) -> dict[str, VersionNodeProgress]:
    result: dict[str, VersionNodeProgress] = {}
    for key, state in states.items():
        result[key] = VersionNodeProgress(
            version_id="ver-1",
            node_key=key,
            state=state,
        )
    return result


def _default_defs() -> list[VersionWorkflowNodeDef]:
    return [
        VersionWorkflowNodeDef(
            project_id="proj-1",
            version_type="app_release",
            **item,
        )
        for item in DEFAULT_APP_RELEASE_WORKFLOW_NODES
    ]


def test_compute_status_planning_default():
    defs = _default_defs()
    nodes = _nodes({k: VersionNodeState.pending.value for k in ("planning", "development")})
    assert compute_version_status(nodes, defs) == VersionStatus.planning


def test_compute_status_developing():
    defs = _default_defs()
    nodes = _nodes(
        {
            "planning": VersionNodeState.completed.value,
            "development": VersionNodeState.pending.value,
        }
    )
    assert compute_version_status(nodes, defs) == VersionStatus.developing


def test_compute_status_releasing():
    defs = _default_defs()
    nodes = _nodes(
        {
            "planning": VersionNodeState.completed.value,
            "development": VersionNodeState.completed.value,
            "release_verification": VersionNodeState.pending.value,
        }
    )
    assert compute_version_status(nodes, defs) == VersionStatus.releasing


def test_compute_status_reviewing():
    defs = _default_defs()
    nodes = _nodes(
        {
            "planning": VersionNodeState.completed.value,
            "development": VersionNodeState.completed.value,
            "release_verification": VersionNodeState.completed.value,
            "gp_review": VersionNodeState.pending.value,
        }
    )
    assert compute_version_status(nodes, defs) == VersionStatus.reviewing


def test_compute_status_ended():
    defs = _default_defs()
    nodes = _nodes({"live": VersionNodeState.completed.value})
    assert compute_version_status(nodes, defs) == VersionStatus.ended


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
        "gp_approved",
        "as_approved",
        "live",
    ):
        db_nodes[key] = VersionNodeProgress(
            version_id="ver-1",
            node_key=key,
            state=VersionNodeState.pending.value,
        )
    for key in (
        "planning",
        "development",
        "release_verification",
        "gp_review",
        "as_review",
        "website_link",
        "gp_approved",
        "as_approved",
    ):
        db_nodes[key].state = VersionNodeState.completed.value

    class FakeSession:
        async def flush(self):
            pass

    import app.services.version_workflow as wf

    defs = _default_defs()

    async def fake_load(db, version_id):
        return db_nodes

    async def fake_load_defs(db, project_id, version_type):
        return defs

    original_load = wf.load_version_nodes
    original_defs = wf.load_project_version_workflow_defs
    wf.load_version_nodes = fake_load
    wf.load_project_version_workflow_defs = fake_load_defs
    try:
        await complete_version_node(FakeSession(), version, "live", "op-1")
    finally:
        wf.load_version_nodes = original_load
        wf.load_project_version_workflow_defs = original_defs

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

    defs = _default_defs()

    async def fake_load(db, vid):
        return db_nodes

    async def fake_load_defs(db, project_id, version_type):
        return defs

    original_load = wf.load_version_nodes
    original_defs = wf.load_project_version_workflow_defs
    wf.load_version_nodes = fake_load
    wf.load_project_version_workflow_defs = fake_load_defs
    try:
        with pytest.raises(VersionWorkflowError, match="版本规划"):
            await complete_version_node(FakeSession(), version, "development", "op-1")
    finally:
        wf.load_version_nodes = original_load
        wf.load_project_version_workflow_defs = original_defs


@pytest.mark.asyncio
async def test_complete_planning_auto_starts_development():
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
        "release_verification": VersionNodeProgress(
            version_id="ver-1", node_key="release_verification", state=VersionNodeState.pending.value
        ),
    }

    class FakeSession:
        async def flush(self):
            pass

    import app.services.version_workflow as wf

    defs = _default_defs()

    async def fake_load(db, vid):
        return db_nodes

    async def fake_load_defs(db, project_id, version_type):
        return defs

    original_load = wf.load_version_nodes
    original_defs = wf.load_project_version_workflow_defs
    wf.load_version_nodes = fake_load
    wf.load_project_version_workflow_defs = fake_load_defs
    try:
        await complete_version_node(FakeSession(), version, "planning", "op-1")
    finally:
        wf.load_version_nodes = original_load
        wf.load_project_version_workflow_defs = original_defs

    assert db_nodes["planning"].state == VersionNodeState.completed.value
    assert db_nodes["development"].state == VersionNodeState.in_progress.value
    assert db_nodes["release_verification"].state == VersionNodeState.pending.value


@pytest.mark.asyncio
async def test_auto_start_first_node_without_prerequisites():
    db_nodes = {
        "planning": VersionNodeProgress(
            version_id="ver-1", node_key="planning", state=VersionNodeState.pending.value
        ),
        "development": VersionNodeProgress(
            version_id="ver-1", node_key="development", state=VersionNodeState.pending.value
        ),
    }

    auto_start_ready_version_nodes(db_nodes, _default_defs(), actor_id="u1")

    assert db_nodes["planning"].state == VersionNodeState.in_progress.value
    assert db_nodes["development"].state == VersionNodeState.pending.value


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

    defs = _default_defs()

    async def fake_load(db, vid):
        return db_nodes

    async def fake_load_defs(db, project_id, version_type):
        return defs

    original_load = wf.load_version_nodes
    original_defs = wf.load_project_version_workflow_defs
    wf.load_version_nodes = fake_load
    wf.load_project_version_workflow_defs = fake_load_defs
    try:
        await reopen_version_node(FakeSession(), version, "gp_review")
    finally:
        wf.load_version_nodes = original_load
        wf.load_project_version_workflow_defs = original_defs

    assert db_nodes["gp_review"].state == VersionNodeState.in_progress.value
    assert db_nodes["as_review"].state == VersionNodeState.completed.value
    assert db_nodes["website_link"].state == VersionNodeState.completed.value
    assert db_nodes["live"].state == VersionNodeState.pending.value
    assert version.status == VersionStatus.reviewing.value


def _defs_with_link_verify() -> list[VersionWorkflowNodeDef]:
    defs = _default_defs()
    defs.append(
        VersionWorkflowNodeDef(
            project_id="proj-1",
            version_type="app_release",
            node_key="link_verify",
            label="链接验证",
            lane_index=5,
            lane_indexes=[5],
            sort_in_lane=2,
        )
    )
    return defs


@pytest.mark.asyncio
async def test_ensure_started_backfills_missing_node_and_auto_starts():
    version = ProjectVersion(
        id="ver-1",
        project_id="proj-1",
        num=1,
        name="v1.1.0",
        version_type="app_release",
        status=VersionStatus.reviewing.value,
        created_by="u1",
    )
    db_nodes = {
        k: VersionNodeProgress(
            version_id="ver-1",
            node_key=k,
            state=VersionNodeState.completed.value,
        )
        for k in (
            "planning",
            "development",
            "release_verification",
            "gp_review",
            "as_review",
            "website_link",
            "gp_approved",
            "as_approved",
        )
    }
    db_nodes["live"] = VersionNodeProgress(
        version_id="ver-1",
        node_key="live",
        state=VersionNodeState.pending.value,
    )

    class FakeSession:
        def __init__(self):
            self.added: list[VersionNodeProgress] = []

        def add(self, row):
            self.added.append(row)
            db_nodes[row.node_key] = row

        async def flush(self):
            pass

    import app.services.version_workflow as wf

    defs = _defs_with_link_verify()
    db = FakeSession()

    async def fake_load(db_arg, version_id):
        return db_nodes

    async def fake_load_defs(db_arg, project_id, version_type):
        return defs

    original_load = wf.load_version_nodes
    original_defs = wf.load_project_version_workflow_defs
    original_backfill = wf._backfill_missing_version_nodes
    wf.load_version_nodes = fake_load
    wf.load_project_version_workflow_defs = fake_load_defs

    async def fake_backfill(db_arg, version_id, nodes, defs_arg):
        added: list[str] = []
        for d in defs_arg:
            if d.node_key in nodes:
                continue
            row = VersionNodeProgress(
                version_id=version_id,
                node_key=d.node_key,
                state=VersionNodeState.pending.value,
            )
            db_arg.add(row)
            added.append(d.node_key)
        return added

    wf._backfill_missing_version_nodes = fake_backfill
    try:
        started, _ = await ensure_version_workflow_nodes_started(db, version, actor_id="u1")
    finally:
        wf.load_version_nodes = original_load
        wf.load_project_version_workflow_defs = original_defs
        wf._backfill_missing_version_nodes = original_backfill

    assert "link_verify" in db_nodes
    assert db_nodes["link_verify"].state == VersionNodeState.in_progress.value
    assert "link_verify" in started


@pytest.mark.asyncio
async def test_sync_version_progress_for_new_def_adds_missing_progress():
    version = ProjectVersion(
        id="ver-1",
        project_id="proj-1",
        num=1,
        name="v1.1.0",
        version_type="app_release",
        status=VersionStatus.reviewing.value,
        created_by="u1",
    )
    db_nodes = {
        k: VersionNodeProgress(
            version_id="ver-1",
            node_key=k,
            state=VersionNodeState.completed.value,
        )
        for k in (
            "planning",
            "development",
            "release_verification",
            "gp_review",
            "as_review",
            "website_link",
            "gp_approved",
            "as_approved",
        )
    }
    db_nodes["live"] = VersionNodeProgress(
        version_id="ver-1",
        node_key="live",
        state=VersionNodeState.pending.value,
    )

    class FakeResult:
        def scalars(self):
            return self

        def all(self):
            return [version]

    class FakeSession:
        def __init__(self):
            self.added: list[VersionNodeProgress] = []

        def add(self, row):
            self.added.append(row)
            db_nodes[row.node_key] = row

        async def execute(self, stmt):
            return FakeResult()

        async def flush(self):
            pass

    import app.services.version_workflow as wf

    defs = _defs_with_link_verify()
    db = FakeSession()

    async def fake_load(db_arg, version_id):
        return db_nodes

    async def fake_load_defs(db_arg, project_id, version_type):
        return defs

    original_load = wf.load_version_nodes
    original_defs = wf.load_project_version_workflow_defs
    wf.load_version_nodes = fake_load
    wf.load_project_version_workflow_defs = fake_load_defs
    try:
        await sync_version_progress_for_new_def(db, "proj-1", "app_release", "link_verify")
    finally:
        wf.load_version_nodes = original_load
        wf.load_project_version_workflow_defs = original_defs

    assert "link_verify" in db_nodes
    assert db_nodes["link_verify"].state == VersionNodeState.in_progress.value
    assert len(db.added) == 1
    assert db.added[0].node_key == "link_verify"


@pytest.mark.asyncio
async def test_sync_version_progress_for_new_def_skips_existing():
    version = ProjectVersion(
        id="ver-1",
        project_id="proj-1",
        num=1,
        name="v1.1.0",
        version_type="app_release",
        created_by="u1",
    )
    db_nodes = {
        "link_verify": VersionNodeProgress(
            version_id="ver-1",
            node_key="link_verify",
            state=VersionNodeState.pending.value,
        ),
    }

    class FakeResult:
        def scalars(self):
            return self

        def all(self):
            return [version]

    class FakeSession:
        def __init__(self):
            self.added: list[VersionNodeProgress] = []

        def add(self, row):
            self.added.append(row)

        async def execute(self, stmt):
            return FakeResult()

        async def flush(self):
            pass

    import app.services.version_workflow as wf

    async def fake_load(db_arg, version_id):
        return db_nodes

    async def fake_load_defs(db_arg, project_id, version_type):
        return _defs_with_link_verify()

    original_load = wf.load_version_nodes
    original_defs = wf.load_project_version_workflow_defs
    wf.load_version_nodes = fake_load
    wf.load_project_version_workflow_defs = fake_load_defs
    db = FakeSession()
    try:
        await sync_version_progress_for_new_def(db, "proj-1", "app_release", "link_verify")
    finally:
        wf.load_version_nodes = original_load
        wf.load_project_version_workflow_defs = original_defs

    assert len(db.added) == 0


@pytest.mark.asyncio
async def test_assert_version_workflow_node_deletable_blocks_in_progress():
    class FakeSession:
        async def execute(self, stmt):
            class R:
                def scalar(self):
                    return 1

            return R()

    with pytest.raises(VersionWorkflowError, match="节点进行中"):
        await assert_version_workflow_node_deletable(
            FakeSession(), "proj-1", "app_release", "link_test"
        )


@pytest.mark.asyncio
async def test_assert_version_workflow_node_deletable_allows_when_idle():
    class FakeSession:
        async def execute(self, stmt):
            class R:
                def scalar(self):
                    return 0

            return R()

    await assert_version_workflow_node_deletable(
        FakeSession(), "proj-1", "app_release", "link_test"
    )
