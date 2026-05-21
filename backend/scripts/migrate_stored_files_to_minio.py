#!/usr/bin/env python3
"""将 stored_files.content（MySQL）一次性迁到 MinIO。需在执行 002 迁移（删 content 列）之前运行。"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import select, text

from app.core.database import engine
from app.services import minio_storage


async def main() -> None:
    await minio_storage.ensure_bucket()
    migrated = 0
    skipped = 0
    async with engine.begin() as conn:
        # 若已无 content 列则退出
        result = await conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'stored_files' "
                "AND COLUMN_NAME = 'content'"
            )
        )
        if result.scalar_one() == 0:
            print("stored_files.content 列不存在，无需迁移。")
            return

        rows = await conn.execute(
            text(
                "SELECT storage_key, content_type, content FROM stored_files "
                "WHERE content IS NOT NULL AND LENGTH(content) > 0"
            )
        )
        for storage_key, content_type, content in rows.fetchall():
            existing = await minio_storage.get_object_bytes(storage_key)
            if existing is not None:
                skipped += 1
                continue
            await minio_storage.put_object(storage_key, content, content_type or "application/octet-stream")
            migrated += 1

    print(f"完成：上传 MinIO {migrated} 个，已存在跳过 {skipped} 个。")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
