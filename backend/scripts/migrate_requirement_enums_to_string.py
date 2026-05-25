#!/usr/bin/env python3
"""Convert requirements.priority/req_type to VARCHAR and add custom_fields JSON column."""
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
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'requirements'"
            )
        )
        col_names = {r[0] for r in cols.all()}

        if "custom_fields" not in col_names:
            await conn.execute(
                text(
                    "ALTER TABLE requirements "
                    "ADD COLUMN custom_fields JSON NOT NULL DEFAULT (JSON_OBJECT())"
                )
            )

        await conn.execute(
            text(
                "ALTER TABLE requirements "
                "MODIFY COLUMN priority VARCHAR(32) NOT NULL DEFAULT 'p1'"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE requirements "
                "MODIFY COLUMN req_type VARCHAR(32) NOT NULL DEFAULT 'feature'"
            )
        )

    await engine.dispose()
    print("Migration requirement enums to string complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
