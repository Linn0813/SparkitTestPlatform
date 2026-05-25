#!/usr/bin/env python3
"""Migrate requirement_workflow_node_defs.role_key -> role_keys (JSON array)."""
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

        if "role_keys" not in column_names:
            await conn.execute(
                text("ALTER TABLE requirement_workflow_node_defs ADD COLUMN role_keys JSON NULL")
            )

        if "role_key" in column_names:
            rows = await conn.execute(
                text("SELECT id, role_key FROM requirement_workflow_node_defs WHERE role_keys IS NULL")
            )
            for row_id, role_key in rows.all():
                await conn.execute(
                    text("UPDATE requirement_workflow_node_defs SET role_keys = :keys WHERE id = :id"),
                    {"id": row_id, "keys": json.dumps([role_key])},
                )
            await conn.execute(
                text("ALTER TABLE requirement_workflow_node_defs DROP COLUMN role_key")
            )

        await conn.execute(
            text("UPDATE requirement_workflow_node_defs SET role_keys = JSON_ARRAY('pm') WHERE role_keys IS NULL")
        )
        await conn.execute(
            text("ALTER TABLE requirement_workflow_node_defs MODIFY COLUMN role_keys JSON NOT NULL")
        )

    await engine.dispose()
    print("Migration role_key -> role_keys complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
