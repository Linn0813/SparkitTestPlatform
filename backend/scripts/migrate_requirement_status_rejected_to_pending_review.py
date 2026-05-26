#!/usr/bin/env python3
"""Migrate requirements.status from rejected to pending_review (removed rejected lifecycle)."""
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
            text("UPDATE requirements SET status = 'pending_review' WHERE status = 'rejected'")
        )
        updated = result.rowcount
    await engine.dispose()
    print(f"Updated {updated} requirement(s) from rejected to pending_review.")


if __name__ == "__main__":
    asyncio.run(migrate())
