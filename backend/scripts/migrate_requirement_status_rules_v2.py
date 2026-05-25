#!/usr/bin/env python3
"""Migrate requirement_status_rules to v2 (trigger_type, require_*); reset defaults."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text

from app.core.database import async_session_factory, engine
from app.models import *  # noqa: F401, F403
from app.core.database import Base
from app.services.requirement_status_rules import replace_project_status_rules
from app.services.requirement_workflow import ensure_project_workflow_defs


async def migrate() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for sql in (
            "ALTER TABLE requirement_status_rules ADD COLUMN trigger_type VARCHAR(32) NOT NULL DEFAULT 'lane'",
            "ALTER TABLE requirement_status_rules ADD COLUMN require_completed JSON NOT NULL",
            "ALTER TABLE requirement_status_rules ADD COLUMN require_incomplete JSON NOT NULL",
        ):
            try:
                await conn.execute(text(sql))
            except Exception:
                pass
        for sql in (
            "ALTER TABLE requirement_status_rules DROP COLUMN in_progress_node_key",
            "ALTER TABLE requirement_status_rules DROP COLUMN active_status",
        ):
            try:
                await conn.execute(text(sql))
            except Exception:
                pass

    from app.constants.requirement_status_rules import DEFAULT_REQUIREMENT_STATUS_RULES

    default_payload = [
        {
            "status": r.status,
            "node_keys": list(r.node_keys),
            "sort": r.sort,
            "trigger_type": r.trigger_type,
            "require_completed": list(r.require_completed),
            "require_incomplete": list(r.require_incomplete),
        }
        for r in DEFAULT_REQUIREMENT_STATUS_RULES
    ]

    project_ids: list[str] = []
    async with async_session_factory() as db:
        result = await db.execute(text("SELECT id FROM projects"))
        project_ids = [row[0] for row in result.fetchall()]
        for pid in project_ids:
            defs = await ensure_project_workflow_defs(db, pid)
            await db.execute(
                text("DELETE FROM requirement_status_rules WHERE project_id = :pid"),
                {"pid": pid},
            )
            await db.flush()
            await replace_project_status_rules(db, pid, default_payload, workflow_defs=defs)
        await db.commit()

    await engine.dispose()
    print(f"Migration requirement_status_rules_v2 complete ({len(project_ids)} projects).")


if __name__ == "__main__":
    asyncio.run(migrate())
