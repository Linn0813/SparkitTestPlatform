#!/usr/bin/env python3
"""Create requirement_node_tasks table and seed default tasks for existing requirements."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import func, select

from app.core.database import Base, async_session_factory, engine
from app.models import *  # noqa: F401, F403
from app.models.requirement import Requirement, RequirementNodeProgress, RequirementNodeTask
from app.services.requirement_node_tasks import (
    fill_empty_task_assignees_from_requirement,
    seed_default_tasks_for_requirement,
)
from app.services.requirement_workflow import load_project_workflow_defs


async def migrate() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        reqs = list((await db.execute(select(Requirement))).scalars().all())
        for req in reqs:
            defs = await load_project_workflow_defs(db, req.project_id)
            def_by_key = {d.node_key: d for d in defs}
            progress_rows = list(
                (
                    await db.execute(
                        select(RequirementNodeProgress).where(
                            RequirementNodeProgress.requirement_id == req.id
                        )
                    )
                ).scalars().all()
            )
            await seed_default_tasks_for_requirement(
                db, req, progress_rows, def_by_key, only_if_empty=True
            )
            await fill_empty_task_assignees_from_requirement(db, req)
        await db.commit()

    await engine.dispose()
    print("Migration requirement_node_tasks complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
