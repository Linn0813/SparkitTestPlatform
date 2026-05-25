#!/usr/bin/env python3
"""Add 'requirement' to project_field_templates.scene ENUM."""
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
            text(
                "ALTER TABLE project_field_templates "
                "MODIFY COLUMN scene ENUM('functional_case', 'bug', 'requirement') NOT NULL"
            )
        )
    await engine.dispose()
    print("Migration template scene requirement complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
