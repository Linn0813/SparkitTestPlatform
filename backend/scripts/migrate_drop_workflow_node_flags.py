#!/usr/bin/env python3
"""Drop is_system and is_required from requirement_workflow_node_defs."""
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
                "WHERE TABLE_SCHEMA = DATABASE() "
                "AND TABLE_NAME = 'requirement_workflow_node_defs'"
            )
        )
        column_names = {row[0] for row in cols.all()}

        if "is_system" in column_names:
            await conn.execute(
                text("ALTER TABLE requirement_workflow_node_defs DROP COLUMN is_system")
            )
        if "is_required" in column_names:
            await conn.execute(
                text("ALTER TABLE requirement_workflow_node_defs DROP COLUMN is_required")
            )

    await engine.dispose()
    print("Dropped is_system / is_required from requirement_workflow_node_defs.")


if __name__ == "__main__":
    asyncio.run(migrate())
