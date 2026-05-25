#!/usr/bin/env python3
"""Add fix_estimate_points and schedule columns to bug_follower_links."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text

from app.core.database import Base, engine
from app.models import *  # noqa: F401, F403


async def migrate() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        alters = [
            "ALTER TABLE bug_follower_links ADD COLUMN fix_estimate_points FLOAT NULL",
            "ALTER TABLE bug_follower_links ADD COLUMN scheduled_start DATE NULL",
            "ALTER TABLE bug_follower_links ADD COLUMN scheduled_end DATE NULL",
        ]
        for sql in alters:
            try:
                await conn.execute(text(sql))
            except Exception:
                pass

    await engine.dispose()
    print("Migration bug_follower_schedule complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
