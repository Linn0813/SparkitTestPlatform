#!/usr/bin/env python3
"""Migrate requirement workflow: node defs table + progress.enabled."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text

from app.core.database import Base, engine
from app.models import *  # noqa: F401, F403
from app.services.requirement_workflow_defaults import DEFAULT_REQUIREMENT_WORKFLOW_NODES


async def migrate() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        try:
            await conn.execute(
                text(
                    "ALTER TABLE requirement_node_progress "
                    "ADD COLUMN enabled TINYINT(1) NOT NULL DEFAULT 1"
                )
            )
        except Exception:
            pass

        await conn.execute(text("UPDATE requirement_node_progress SET enabled = 1"))

        projects = await conn.execute(text("SELECT id FROM projects"))
        project_ids = [r[0] for r in projects.all()]

        for pid in project_ids:
            for item in DEFAULT_REQUIREMENT_WORKFLOW_NODES:
                await conn.execute(
                    text(
                        "INSERT IGNORE INTO requirement_workflow_node_defs "
                        "(id, project_id, node_key, label, role_keys, lane_index, sort_in_lane, "
                        "created_at, updated_at) "
                        "VALUES (UUID(), :pid, :key, :label, :roles, :lane, :sort, NOW(), NOW())"
                    ),
                    {
                        "pid": pid,
                        "key": item["node_key"],
                        "label": item["label"],
                        "roles": json.dumps(item["role_keys"]),
                        "lane": item["lane_index"],
                        "sort": item["sort_in_lane"],
                    },
                )

            reqs = await conn.execute(text("SELECT id FROM requirements WHERE project_id = :pid"), {"pid": pid})
            for (rid,) in reqs.all():
                defs = await conn.execute(
                    text("SELECT node_key FROM requirement_workflow_node_defs WHERE project_id = :pid"),
                    {"pid": pid},
                )
                for (node_key,) in defs.all():
                    exists = await conn.execute(
                        text(
                            "SELECT id FROM requirement_node_progress "
                            "WHERE requirement_id = :rid AND node_key = :key"
                        ),
                        {"rid": rid, "key": node_key},
                    )
                    if exists.first():
                        continue
                    await conn.execute(
                        text(
                            "INSERT INTO requirement_node_progress "
                            "(id, requirement_id, node_key, state, enabled, created_at, updated_at) "
                            "VALUES (UUID(), :rid, :key, 'pending', 0, NOW(), NOW())"
                        ),
                        {"rid": rid, "key": node_key},
                    )

    await engine.dispose()
    print(f"Migration complete for {len(project_ids)} projects.")


if __name__ == "__main__":
    asyncio.run(migrate())
