#!/usr/bin/env python3
"""Add version_type to version_status_rules; seed hotfix defaults for existing projects."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import select

from app.core.database import async_session_factory, engine
from app.core.schema_patches import ensure_schema_patches
from app.models import *  # noqa: F401, F403
from app.models.project import Project
from app.models.template import VersionStatusRule
from app.services.version_status_rules import ensure_project_version_status_rules
from app.services.version_workflow_defs import ensure_project_version_workflow_defs


async def migrate() -> None:
    await ensure_schema_patches()

    async with async_session_factory() as db:
        result = await db.execute(select(Project.id))
        project_ids = [row[0] for row in result.fetchall()]
        for pid in project_ids:
            await ensure_project_version_workflow_defs(db, pid)
            for version_type in ("app_release", "hotfix"):
                existing = await db.execute(
                    select(VersionStatusRule.id)
                    .where(
                        VersionStatusRule.project_id == pid,
                        VersionStatusRule.version_type == version_type,
                    )
                    .limit(1)
                )
                if existing.scalar_one_or_none() is None:
                    await ensure_project_version_status_rules(db, pid, version_type)
        await db.commit()

    await engine.dispose()
    print(f"Migration version_status_rules_by_type complete ({len(project_ids)} projects).")


if __name__ == "__main__":
    asyncio.run(migrate())
