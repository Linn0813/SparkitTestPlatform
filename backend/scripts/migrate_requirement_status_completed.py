#!/usr/bin/env python3
"""Add requirements.status value 'completed' and seed status_hold rule for existing projects."""
from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import select, text

from app.core.database import async_session_factory, engine
from app.models import *  # noqa: F401, F403
from app.models.template import RequirementStatusRule


async def migrate() -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text("ALTER TABLE requirements MODIFY COLUMN status VARCHAR(32) NOT NULL DEFAULT 'draft'")
        )
        await conn.execute(
            text(
                "ALTER TABLE requirements MODIFY COLUMN status "
                "ENUM('draft','pending_review','designing','developing','testing',"
                "'pending_release','released','rejected','completed','closed') NOT NULL DEFAULT 'draft'"
            )
        )

    inserted = 0
    async with async_session_factory() as db:
        result = await db.execute(text("SELECT id FROM projects"))
        project_ids = [row[0] for row in result.fetchall()]
        for pid in project_ids:
            existing = await db.execute(
                select(RequirementStatusRule).where(
                    RequirementStatusRule.project_id == pid,
                    RequirementStatusRule.status == "completed",
                    RequirementStatusRule.trigger_type == "status_hold",
                )
            )
            if existing.scalar_one_or_none():
                continue
            db.add(
                RequirementStatusRule(
                    id=str(uuid.uuid4()),
                    project_id=pid,
                    status="completed",
                    node_keys=[],
                    sort=0,
                    trigger_type="status_hold",
                )
            )
            inserted += 1
        await db.commit()

    await engine.dispose()
    print(f"Migration requirement_status_completed complete ({inserted} projects updated).")


if __name__ == "__main__":
    asyncio.run(migrate())
