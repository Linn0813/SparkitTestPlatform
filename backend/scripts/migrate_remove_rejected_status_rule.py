#!/usr/bin/env python3
"""Remove rejected status_hold rows from requirement_status_rules (use code sticky instead)."""
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
        result = await conn.execute(
            text(
                "DELETE FROM requirement_status_rules "
                "WHERE trigger_type = 'status_hold' AND status = 'rejected'"
            )
        )
        deleted = result.rowcount
    await engine.dispose()
    print(f"Removed {deleted} rejected status_hold rule(s).")


if __name__ == "__main__":
    asyncio.run(migrate())
