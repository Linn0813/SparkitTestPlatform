#!/usr/bin/env python3
"""Drop require_completed/require_incomplete; reseed default rules without rejected."""
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
from app.services.requirement_status_rules import _default_payload_from_constants


async def migrate() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for sql in (
            "ALTER TABLE requirement_status_rules DROP COLUMN require_completed",
            "ALTER TABLE requirement_status_rules DROP COLUMN require_incomplete",
        ):
            try:
                await conn.execute(text(sql))
            except Exception:
                pass

    project_ids: list[str] = []
    payload = _default_payload_from_constants()
    async with async_session_factory() as db:
        result = await db.execute(text("SELECT id FROM projects"))
        project_ids = [row[0] for row in result.fetchall()]
        for pid in project_ids:
            await db.execute(
                text("DELETE FROM requirement_status_rules WHERE project_id = :pid"),
                {"pid": pid},
            )
            await db.flush()
            defs = await ensure_project_workflow_defs(db, pid)
            await replace_project_status_rules(db, pid, payload, workflow_defs=defs)
        await db.commit()

    await engine.dispose()
    print(f"Migration requirement_status_rules_v3 complete ({len(project_ids)} projects).")


if __name__ == "__main__":
    asyncio.run(migrate())
