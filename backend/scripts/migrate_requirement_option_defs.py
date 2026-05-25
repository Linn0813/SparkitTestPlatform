#!/usr/bin/env python3
"""Create requirement_option_defs table and seed default priority/type options."""
from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text

from app.core.database import Base, engine
from app.models import *  # noqa: F401, F403

DEFAULT_OPTIONS: list[tuple[str, str, str, int]] = [
    ("priority", "p00", "P00", 0),
    ("priority", "p0", "P0", 1),
    ("priority", "p1", "P1", 2),
    ("req_type", "feature", "需求开发", 0),
    ("req_type", "tech_optimization", "技术优化", 1),
]


async def migrate() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        projects = await conn.execute(text("SELECT id FROM projects"))
        project_ids = [r[0] for r in projects.all()]

        for project_id in project_ids:
            for category, option_key, label, sort in DEFAULT_OPTIONS:
                existing = await conn.execute(
                    text(
                        "SELECT id FROM requirement_option_defs "
                        "WHERE project_id = :pid AND category = :cat AND option_key = :key LIMIT 1"
                    ),
                    {"pid": project_id, "cat": category, "key": option_key},
                )
                if existing.first() is not None:
                    continue
                await conn.execute(
                    text(
                        "INSERT INTO requirement_option_defs "
                        "(id, project_id, category, option_key, label, sort) "
                        "VALUES (:id, :pid, :cat, :key, :label, :sort)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "pid": project_id,
                        "cat": category,
                        "key": option_key,
                        "label": label,
                        "sort": sort,
                    },
                )

    await engine.dispose()
    print(f"Migration requirement_option_defs complete. Seeded {len(project_ids)} projects.")


if __name__ == "__main__":
    asyncio.run(migrate())
