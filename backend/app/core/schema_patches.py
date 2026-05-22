from __future__ import annotations

import logging

from sqlalchemy import text

from app.core.database import engine

logger = logging.getLogger(__name__)


async def _column_exists(conn, table: str, column: str) -> bool:
    result = await conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table "
            "AND COLUMN_NAME = :column"
        ),
        {"table": table, "column": column},
    )
    return result.scalar_one() > 0


async def _index_exists(conn, table: str, index_name: str) -> bool:
    result = await conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table "
            "AND INDEX_NAME = :index_name"
        ),
        {"table": table, "index_name": index_name},
    )
    return result.scalar_one() > 0


async def ensure_schema_patches() -> None:
    """对已有库补列（create_all 不会 ALTER 已有表）。"""
    column_patches = (
        ("project_integrations", "app_public_url", "ALTER TABLE project_integrations ADD COLUMN app_public_url TEXT NULL"),
        ("bug_wecom_notify_rules", "from_status_keys", "ALTER TABLE bug_wecom_notify_rules ADD COLUMN from_status_keys JSON NULL"),
        ("bug_wecom_notify_rules", "to_status_keys", "ALTER TABLE bug_wecom_notify_rules ADD COLUMN to_status_keys JSON NULL"),
    )
    async with engine.begin() as conn:
        for table, column, ddl in column_patches:
            if not await _column_exists(conn, table, column):
                await conn.execute(text(ddl))
                logger.info("Schema patch applied: %s.%s", table, column)

        if await _index_exists(conn, "bug_wecom_notify_rules", "uq_wecom_notify_rule"):
            await conn.execute(text("ALTER TABLE bug_wecom_notify_rules DROP INDEX uq_wecom_notify_rule"))
            logger.info("Schema patch applied: dropped uq_wecom_notify_rule")

        if await _column_exists(conn, "bug_wecom_notify_rules", "from_status_keys"):
            await conn.execute(
                text(
                    """
                    UPDATE bug_wecom_notify_rules
                    SET from_status_keys = JSON_ARRAY(from_status_key),
                        to_status_keys = JSON_ARRAY(to_status_key)
                    WHERE kind = 'transition'
                      AND from_status_key IS NOT NULL
                      AND (from_status_keys IS NULL OR JSON_LENGTH(from_status_keys) = 0)
                    """
                )
            )
