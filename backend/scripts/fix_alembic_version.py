#!/usr/bin/env python3
"""修复 alembic_version 中无效/过长 revision，并补 project_versions.build_number。"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

CURRENT_REVISION = "003_build_number"


async def main() -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    async with engine.begin() as conn:
        tables = await conn.execute(text("SHOW TABLES LIKE 'alembic_version'"))
        if tables.fetchone():
            await conn.execute(text("DELETE FROM alembic_version"))
            await conn.execute(
                text("ALTER TABLE alembic_version MODIFY version_num VARCHAR(64) NOT NULL")
            )
            print("✓ 已清空 alembic_version 并扩展 version_num 至 VARCHAR(64)")
        else:
            await conn.execute(
                text(
                    "CREATE TABLE alembic_version ("
                    "version_num VARCHAR(64) NOT NULL, "
                    "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)"
                    ")"
                )
            )
            print("✓ 已创建 alembic_version 表")

        result = await conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'project_versions' "
                "AND COLUMN_NAME = 'build_number'"
            )
        )
        if result.scalar_one() == 0:
            await conn.execute(
                text(
                    "ALTER TABLE project_versions "
                    "ADD COLUMN build_number VARCHAR(64) NULL AFTER name"
                )
            )
            print("✓ 已添加 project_versions.build_number")
        else:
            print("ℹ project_versions.build_number 已存在")

        await conn.execute(
            text("DELETE FROM alembic_version")
        )
        await conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:rev)"),
            {"rev": CURRENT_REVISION},
        )
        print(f"✓ alembic 版本已标记为 {CURRENT_REVISION}")

    await engine.dispose()
    print("完成。可重启后端验证 /versions 接口。")


if __name__ == "__main__":
    asyncio.run(main())
