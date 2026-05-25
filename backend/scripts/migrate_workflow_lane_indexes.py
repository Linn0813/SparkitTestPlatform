#!/usr/bin/env python3
"""Add lane_indexes and blocks_lane_gate to requirement_workflow_node_defs."""
from __future__ import annotations

import asyncio
import json
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

        if "lane_indexes" not in column_names:
            await conn.execute(
                text("ALTER TABLE requirement_workflow_node_defs ADD COLUMN lane_indexes JSON NULL")
            )
        if "blocks_lane_gate" not in column_names:
            await conn.execute(
                text(
                    "ALTER TABLE requirement_workflow_node_defs "
                    "ADD COLUMN blocks_lane_gate TINYINT(1) NOT NULL DEFAULT 1"
                )
            )

        rows = await conn.execute(text("SELECT id, lane_index FROM requirement_workflow_node_defs"))
        for row_id, lane_index in rows.all():
            await conn.execute(
                text("UPDATE requirement_workflow_node_defs SET lane_indexes = :lanes WHERE id = :id"),
                {"id": row_id, "lanes": json.dumps([lane_index])},
            )

        await conn.execute(
            text(
                "UPDATE requirement_workflow_node_defs SET lane_indexes = JSON_ARRAY(0) "
                "WHERE lane_indexes IS NULL"
            )
        )
        await conn.execute(
            text("ALTER TABLE requirement_workflow_node_defs MODIFY COLUMN lane_indexes JSON NOT NULL")
        )

    await engine.dispose()
    print("Migration lane_indexes / blocks_lane_gate complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
