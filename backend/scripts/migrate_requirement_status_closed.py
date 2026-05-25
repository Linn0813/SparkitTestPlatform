#!/usr/bin/env python3
"""Add requirements.status value 'closed'."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text

from app.core.database import engine


async def migrate() -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text("ALTER TABLE requirements MODIFY COLUMN status VARCHAR(32) NOT NULL DEFAULT 'draft'")
        )
        await conn.execute(
            text(
                "ALTER TABLE requirements MODIFY COLUMN status "
                "ENUM('draft','pending_review','designing','developing','testing',"
                "'pending_release','released','rejected','closed') NOT NULL DEFAULT 'draft'"
            )
        )
    await engine.dispose()
    print("Migration requirement_status_closed complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
