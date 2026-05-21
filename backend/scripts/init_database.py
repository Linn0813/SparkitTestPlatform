#!/usr/bin/env python3
"""Create database (if missing) and all tables from SQLAlchemy models."""
from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.database import Base, engine
from app.models import *  # noqa: F401, F403


def _parse_mysql_url(url: str) -> tuple[str, str]:
    """Return (server_url without db path, database_name)."""
    m = re.match(
        r"^(mysql\+aiomysql://[^/]+)(?:/([^?]+))?(?:\?.*)?$",
        url.strip(),
    )
    if not m:
        raise SystemExit(f"Invalid DATABASE_URL (expected mysql+aiomysql://.../dbname): {url}")
    server = m.group(1)
    db_name = (m.group(2) or "").strip()
    if not db_name:
        raise SystemExit("DATABASE_URL must include a database name, e.g. .../sparkit")
    return server, db_name


async def ensure_database() -> None:
    server_url, db_name = _parse_mysql_url(settings.database_url)
    admin_engine = create_async_engine(f"{server_url}/mysql", pool_pre_ping=True)
    try:
        async with admin_engine.connect() as conn:
            await conn.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
            await conn.commit()
        print(f"Database `{db_name}` ready.")
    finally:
        await admin_engine.dispose()


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created (create_all).")


async def main() -> None:
    await ensure_database()
    await create_tables()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
