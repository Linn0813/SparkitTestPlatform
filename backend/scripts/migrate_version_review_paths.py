"""Patch app_release review paths, node progress fields, and reset version workflows."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import delete, select, text

from app.constants.version_types import VersionType
from app.core.database import async_session_factory, engine
from app.models.project import Project
from app.models.project_version import ProjectVersion
from app.models.template import VersionWorkflowNodeDef
from app.models.version_workflow import VersionNodeProgress
from app.services.version_workflow import reset_version_workflow
from app.services.version_workflow_defaults import (
    APP_RELEASE_NODE_KEYS,
    DEFAULT_APP_RELEASE_WORKFLOW_NODES,
)
from app.services.version_workflow_defs import sync_lane_fields


async def migrate() -> None:
    async with engine.begin() as conn:
        for col, ddl in (
            (
                "assignee_id",
                "ADD COLUMN assignee_id VARCHAR(36) NULL AFTER operator_id",
            ),
            (
                "scheduled_start",
                "ADD COLUMN scheduled_start DATE NULL AFTER assignee_id",
            ),
            (
                "scheduled_end",
                "ADD COLUMN scheduled_end DATE NULL AFTER scheduled_start",
            ),
        ):
            exists = await conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'version_node_progress' "
                    f"AND COLUMN_NAME = '{col}'"
                )
            )
            if not exists.scalar():
                await conn.execute(text(f"ALTER TABLE version_node_progress {ddl}"))

    async with async_session_factory() as db:
        projects = (await db.execute(select(Project.id))).scalars().all()
        for project_id in projects:
            existing = (
                await db.execute(
                    select(VersionWorkflowNodeDef).where(
                        VersionWorkflowNodeDef.project_id == project_id,
                        VersionWorkflowNodeDef.version_type == VersionType.app_release.value,
                    )
                )
            ).scalars().all()
            by_key = {d.node_key: d for d in existing}
            for item in DEFAULT_APP_RELEASE_WORKFLOW_NODES:
                row = by_key.get(item["node_key"])
                if row:
                    row.label = item["label"]
                    row.lane_index = item["lane_index"]
                    row.lane_indexes = item["lane_indexes"]
                    row.sort_in_lane = item["sort_in_lane"]
                    sync_lane_fields(row)
                else:
                    row = VersionWorkflowNodeDef(
                        id=str(uuid.uuid4()),
                        project_id=project_id,
                        version_type=VersionType.app_release.value,
                        **item,
                    )
                    sync_lane_fields(row)
                    db.add(row)
            for row in existing:
                if row.node_key not in APP_RELEASE_NODE_KEYS:
                    await db.delete(row)
            await db.flush()

        versions = (await db.execute(select(ProjectVersion))).scalars().all()
        reset_count = 0
        for ver in versions:
            await reset_version_workflow(db, ver)
            reset_count += 1

        await db.commit()
        print(
            f"Migration complete: patched app_release defs for {len(projects)} project(s), "
            f"reset workflow for {reset_count} version(s)."
        )


if __name__ == "__main__":
    asyncio.run(migrate())
