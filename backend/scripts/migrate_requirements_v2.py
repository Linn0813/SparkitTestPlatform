#!/usr/bin/env python3
"""Migrate requirements table to v2 schema and reset workflow state."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text

from app.core.database import engine
from app.models import *  # noqa: F401, F403
from app.core.database import Base


async def migrate() -> None:
    req_ids: list[str] = []
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Add new columns if missing (MySQL)
        alters = [
            "ALTER TABLE requirements ADD COLUMN priority ENUM('p00','p0','p1') NOT NULL DEFAULT 'p1'",
            "ALTER TABLE requirements ADD COLUMN req_type ENUM('feature','tech_optimization') NOT NULL DEFAULT 'feature'",
            "ALTER TABLE requirements ADD COLUMN frontend_rd_id VARCHAR(36) NULL",
            "ALTER TABLE requirements ADD COLUMN backend_rd_id VARCHAR(36) NULL",
            "ALTER TABLE requirements ADD COLUMN pm_id VARCHAR(36) NULL",
            "ALTER TABLE requirements ADD COLUMN tech_owner_id VARCHAR(36) NULL",
            "ALTER TABLE requirements ADD COLUMN qa_id VARCHAR(36) NULL",
            "ALTER TABLE requirements ADD COLUMN designer_id VARCHAR(36) NULL",
        ]
        for sql in alters:
            try:
                await conn.execute(text(sql))
            except Exception:
                pass

        # Expand status column before resetting values
        await conn.execute(text("ALTER TABLE requirements MODIFY COLUMN status VARCHAR(32) NOT NULL DEFAULT 'draft'"))
        await conn.execute(text("UPDATE requirements SET status = 'draft'"))
        await conn.execute(
            text(
                "ALTER TABLE requirements MODIFY COLUMN status "
                "ENUM('draft','pending_review','designing','developing','testing',"
                "'pending_release','released','rejected') NOT NULL DEFAULT 'draft'"
            )
        )

        # Init node progress for existing requirements
        from app.constants.requirement_nodes import REQUIREMENT_NODE_KEYS

        req_rows = await conn.execute(text("SELECT id FROM requirements"))
        req_ids = [r[0] for r in req_rows.all()]
        for rid in req_ids:
            for key in REQUIREMENT_NODE_KEYS:
                await conn.execute(
                    text(
                        "INSERT IGNORE INTO requirement_node_progress "
                        "(id, requirement_id, node_key, state, created_at, updated_at) "
                        "VALUES (UUID(), :rid, :key, 'pending', NOW(), NOW())"
                    ),
                    {"rid": rid, "key": key},
                )

    await engine.dispose()
    print(f"Migration complete. Initialized nodes for {len(req_ids)} requirements.")


if __name__ == "__main__":
    asyncio.run(migrate())
