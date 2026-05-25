#!/usr/bin/env python3
"""Create requirement_comments table."""
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
                "SELECT TABLE_NAME FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'requirement_comments'"
            )
        )
        if cols.first() is None:
            await conn.execute(
                text(
                    """
                    CREATE TABLE requirement_comments (
                        id VARCHAR(36) NOT NULL PRIMARY KEY,
                        requirement_id VARCHAR(36) NOT NULL,
                        user_id VARCHAR(36) NOT NULL,
                        body TEXT NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        INDEX ix_requirement_comments_requirement_id (requirement_id),
                        CONSTRAINT fk_requirement_comments_requirement
                            FOREIGN KEY (requirement_id) REFERENCES requirements(id),
                        CONSTRAINT fk_requirement_comments_user
                            FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                    """
                )
            )
    await engine.dispose()
    print("Migration requirement_comments complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
