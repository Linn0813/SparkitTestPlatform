"""Backfill version workflow nodes and status for existing project_versions."""

from __future__ import annotations

import asyncio

from sqlalchemy import select, text

from app.constants.version_nodes import VERSION_NODE_KEYS
from app.core.database import async_session_factory, engine
from app.models.project_version import ProjectVersion
from app.models.version_workflow import VersionNodeProgress, VersionNodeState, VersionStatus
from app.services.version_workflow import compute_version_status, init_version_workflow, load_version_nodes
from app.services.version_workflow_defs import load_project_version_workflow_defs


async def migrate() -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS version_node_progress ("
                "id VARCHAR(36) PRIMARY KEY, "
                "version_id VARCHAR(36) NOT NULL, "
                "node_key VARCHAR(64) NOT NULL, "
                "state VARCHAR(16) NOT NULL DEFAULT 'pending', "
                "completed_at DATETIME NULL, "
                "operator_id VARCHAR(36) NULL, "
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, "
                "UNIQUE KEY uq_version_node (version_id, node_key), "
                "INDEX ix_version_node_progress_version_id (version_id), "
                "FOREIGN KEY (version_id) REFERENCES project_versions(id) ON DELETE CASCADE"
                ")"
            )
        )
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS version_wecom_notify_rules ("
                "id VARCHAR(36) PRIMARY KEY, "
                "project_id VARCHAR(36) NOT NULL, "
                "event_key VARCHAR(64) NOT NULL, "
                "message_template TEXT NOT NULL, "
                "notify_user_ids JSON NOT NULL, "
                "enabled TINYINT(1) NOT NULL DEFAULT 1, "
                "UNIQUE KEY uq_version_wecom_event (project_id, event_key), "
                "INDEX ix_version_wecom_notify_rules_project_id (project_id), "
                "FOREIGN KEY (project_id) REFERENCES projects(id)"
                ")"
            )
        )

    async with async_session_factory() as db:
        versions = (await db.execute(select(ProjectVersion))).scalars().all()
        initialized = 0
        ended = 0
        for ver in versions:
            existing = await db.execute(
                select(VersionNodeProgress.id).where(VersionNodeProgress.version_id == ver.id).limit(1)
            )
            if existing.scalar_one_or_none():
                continue

            if ver.released_at is not None:
                for key in VERSION_NODE_KEYS:
                    db.add(
                        VersionNodeProgress(
                            version_id=ver.id,
                            node_key=key,
                            state=VersionNodeState.completed.value,
                        )
                    )
                ver.status = VersionStatus.ended.value
                ended += 1
            else:
                await init_version_workflow(db, ver.id, ver.project_id, ver.version_type or "app_release")
                nodes_result = await db.execute(
                    select(VersionNodeProgress).where(VersionNodeProgress.version_id == ver.id)
                )
                nodes = {n.node_key: n for n in nodes_result.scalars().all()}
                defs = await load_project_version_workflow_defs(
                    db, ver.project_id, ver.version_type or "app_release"
                )
                ver.status = compute_version_status(nodes, defs).value
            initialized += 1

        await db.commit()
        print(f"Migration complete: initialized workflow for {initialized} version(s) ({ended} marked ended).")


if __name__ == "__main__":
    asyncio.run(migrate())
