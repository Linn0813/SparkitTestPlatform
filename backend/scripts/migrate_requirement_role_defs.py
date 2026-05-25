#!/usr/bin/env python3
"""Create requirement_role_defs table and seed default roles for all projects."""
from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text

from app.constants.requirement_nodes import REQUIREMENT_ROLE_KEYS, REQUIREMENT_ROLE_LABELS
from app.core.database import Base, engine
from app.models import *  # noqa: F401, F403


async def migrate() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        projects = await conn.execute(text("SELECT id FROM projects"))
        project_ids = [r[0] for r in projects.all()]

        for project_id in project_ids:
            for sort, role_key in enumerate(REQUIREMENT_ROLE_KEYS):
                existing = await conn.execute(
                    text(
                        "SELECT id FROM requirement_role_defs "
                        "WHERE project_id = :pid AND role_key = :key LIMIT 1"
                    ),
                    {"pid": project_id, "key": role_key},
                )
                if existing.first() is not None:
                    continue
                await conn.execute(
                    text(
                        "INSERT INTO requirement_role_defs "
                        "(id, project_id, role_key, label, sort) "
                        "VALUES (:id, :pid, :key, :label, :sort)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "pid": project_id,
                        "key": role_key,
                        "label": REQUIREMENT_ROLE_LABELS.get(role_key, role_key),
                        "sort": sort,
                    },
                )

    await engine.dispose()
    print(f"Migration requirement_role_defs complete. Seeded {len(project_ids)} projects.")


if __name__ == "__main__":
    asyncio.run(migrate())
