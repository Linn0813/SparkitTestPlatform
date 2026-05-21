#!/usr/bin/env python3
"""检查 DATABASE_URL 连通性并列出库/表（便于确认 sparkit 是否已创建）。"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from scripts.init_database import _admin_mysql_url, _parse_mysql_url


async def main() -> None:
    server_url, db_name = _parse_mysql_url(settings.database_url)
    print(f"DATABASE_URL 库名: {db_name}")

    try:
        admin = create_async_engine(_admin_mysql_url(server_url), pool_pre_ping=True)
        async with admin.connect() as conn:
            rows = await conn.execute(text("SHOW DATABASES"))
            dbs = [r[0] for r in rows.fetchall()]
        await admin.dispose()
        print("服务器上的数据库:", ", ".join(dbs))
        if db_name in dbs:
            print(f"✓ 库 `{db_name}` 已存在")
        else:
            print(f"✗ 库 `{db_name}` 不存在，请运行: python scripts/init_database.py")
    except Exception as exc:
        print(f"无法以管理员列出库（可忽略，若下方能连上业务库即可）: {exc}")

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    async with engine.connect() as conn:
        tables = await conn.execute(text("SHOW TABLES"))
        names = [r[0] for r in tables.fetchall()]
    await engine.dispose()
    print(f"库 `{db_name}` 内表数量: {len(names)}")
    if names:
        print("部分表:", ", ".join(sorted(names)[:12]), "..." if len(names) > 12 else "")


if __name__ == "__main__":
    asyncio.run(main())
