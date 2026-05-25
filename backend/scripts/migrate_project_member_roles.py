#!/usr/bin/env python3
"""Migrate project_members.role -> roles (JSON array)."""
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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        try:
            await conn.execute(text("ALTER TABLE project_members ADD COLUMN roles JSON NULL"))
        except Exception:
            pass

        cols = await conn.execute(text("SHOW COLUMNS FROM project_members LIKE 'role'"))
        has_role_col = cols.first() is not None

        if has_role_col:
            await conn.execute(
                text("UPDATE project_members SET roles = JSON_ARRAY(role) WHERE roles IS NULL")
            )
            try:
                await conn.execute(text("ALTER TABLE project_members DROP COLUMN role"))
            except Exception:
                pass

        await conn.execute(
            text(
                "UPDATE project_members SET roles = JSON_ARRAY('member') "
                "WHERE roles IS NULL OR JSON_LENGTH(roles) = 0"
            )
        )
        try:
            await conn.execute(text("ALTER TABLE project_members MODIFY COLUMN roles JSON NOT NULL"))
        except Exception:
            pass

    print("migrate_project_member_roles: done")


if __name__ == "__main__":
    asyncio.run(migrate())
