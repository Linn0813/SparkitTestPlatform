"""Add version_type, version_workflow_node_defs table, and seed default templates."""

from __future__ import annotations

import asyncio

from sqlalchemy import select, text

from app.constants.version_types import VERSION_TYPES
from app.core.database import async_session_factory, engine
from app.models.project import Project
from app.models.project_version import ProjectVersion
from app.models.version_workflow import VersionNodeProgress, VersionNodeState, VersionStatus
from app.services.version_workflow import compute_version_status, init_version_workflow, load_version_nodes
from app.services.version_workflow_defs import ensure_project_version_workflow_defs, load_project_version_workflow_defs


async def migrate() -> None:
    async with engine.begin() as conn:
        col = await conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'project_versions' "
                "AND COLUMN_NAME = 'version_type'"
            )
        )
        if not col.scalar():
            await conn.execute(
                text(
                    "ALTER TABLE project_versions "
                    "ADD COLUMN version_type VARCHAR(32) NOT NULL DEFAULT 'app_release' "
                    "AFTER name"
                )
            )

        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS version_workflow_node_defs ("
                "id VARCHAR(36) PRIMARY KEY, "
                "project_id VARCHAR(36) NOT NULL, "
                "version_type VARCHAR(32) NOT NULL, "
                "node_key VARCHAR(64) NOT NULL, "
                "label VARCHAR(128) NOT NULL, "
                "lane_index INT NOT NULL DEFAULT 0, "
                "lane_indexes JSON NOT NULL, "
                "sort_in_lane INT NOT NULL DEFAULT 0, "
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, "
                "UNIQUE KEY uq_project_version_wf_node (project_id, version_type, node_key), "
                "INDEX ix_version_workflow_node_defs_project_id (project_id), "
                "FOREIGN KEY (project_id) REFERENCES projects(id)"
                ")"
            )
        )

    async with async_session_factory() as db:
        projects = (await db.execute(select(Project.id))).scalars().all()
        for project_id in projects:
            await ensure_project_version_workflow_defs(db, project_id)

        versions = (await db.execute(select(ProjectVersion))).scalars().all()
        backfilled = 0
        for ver in versions:
            if not ver.version_type:
                ver.version_type = "app_release"
            existing = await db.execute(
                select(VersionNodeProgress.id).where(VersionNodeProgress.version_id == ver.id).limit(1)
            )
            if existing.scalar_one_or_none():
                defs = await load_project_version_workflow_defs(db, ver.project_id, ver.version_type)
                nodes = await load_version_nodes(db, ver.id)
                ver.status = compute_version_status(nodes, defs).value
                continue

            if ver.released_at is not None:
                defs = await load_project_version_workflow_defs(db, ver.project_id, ver.version_type)
                for d in defs:
                    db.add(
                        VersionNodeProgress(
                            version_id=ver.id,
                            node_key=d.node_key,
                            state=VersionNodeState.completed.value,
                        )
                    )
                ver.status = VersionStatus.ended.value
            else:
                await init_version_workflow(db, ver.id, ver.project_id, ver.version_type)
                defs = await load_project_version_workflow_defs(db, ver.project_id, ver.version_type)
                nodes = await load_version_nodes(db, ver.id)
                ver.status = compute_version_status(nodes, defs).value
            backfilled += 1

        await db.commit()
        print(
            f"Migration complete: seeded workflow defs for {len(projects)} project(s), "
            f"backfilled {backfilled} version(s)."
        )


if __name__ == "__main__":
    asyncio.run(migrate())
