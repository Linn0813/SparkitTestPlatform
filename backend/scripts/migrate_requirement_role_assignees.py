#!/usr/bin/env python3
"""Add requirements.role_assignee_ids JSON column."""
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
        cols = await conn.execute(
            text(
                "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'requirements' "
                "AND COLUMN_NAME = 'role_assignee_ids'"
            )
        )
        if cols.first() is None:
            await conn.execute(
                text(
                    "ALTER TABLE requirements "
                    "ADD COLUMN role_assignee_ids JSON NOT NULL DEFAULT (JSON_OBJECT())"
                )
            )
    await engine.dispose()
    print("Migration role_assignee_ids complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
