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
        (
            "bug_wecom_notify_rules",
            "entity_type",
            "ALTER TABLE bug_wecom_notify_rules ADD COLUMN entity_type VARCHAR(16) NOT NULL DEFAULT 'bug'",
        ),
        (
            "requirements",
            "selected_role_keys",
            "ALTER TABLE requirements ADD COLUMN selected_role_keys JSON NULL",
        ),
        (
            "project_versions",
            "status",
            "ALTER TABLE project_versions ADD COLUMN status VARCHAR(32) NOT NULL DEFAULT 'planning'",
        ),
        (
            "project_integrations",
            "version_wecom_webhook_url",
            "ALTER TABLE project_integrations ADD COLUMN version_wecom_webhook_url TEXT NULL",
        ),
        (
            "project_integrations",
            "version_wecom_enabled",
            "ALTER TABLE project_integrations ADD COLUMN version_wecom_enabled TINYINT(1) NOT NULL DEFAULT 0",
        ),
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

        if await _column_exists(conn, "bug_wecom_notify_rules", "entity_type"):
            await conn.execute(
                text(
                    """
                    UPDATE bug_wecom_notify_rules
                    SET entity_type = 'bug'
                    WHERE entity_type IS NULL OR entity_type = ''
                    """
                )
            )

    async with engine.begin() as conn:
        if await _column_exists(conn, "requirements", "selected_role_keys"):
            from app.core.database import async_session_factory
            from app.services.requirement_selected_roles import backfill_requirement_selected_role_keys

            async with async_session_factory() as session:
                count = await backfill_requirement_selected_role_keys(session)
                await session.commit()
                if count:
                    logger.info(
                        "Schema patch: backfilled selected_role_keys for %s requirements",
                        count,
                    )

        table = "version_wecom_notify_rules"
        if await _column_exists(conn, table, "event_key") and not await _column_exists(conn, table, "node_key"):
            await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN node_key VARCHAR(64) NULL"))
            await conn.execute(
                text(
                    f"""
                    UPDATE {table}
                    SET node_key = REPLACE(event_key, '_complete', '')
                    WHERE node_key IS NULL
                    """
                )
            )
            logger.info("Schema patch applied: version_wecom_notify_rules.node_key backfill")

        if await _column_exists(conn, table, "node_key") and await _column_exists(conn, table, "event_key"):
            if await _index_exists(conn, table, "uq_version_wecom_event"):
                await conn.execute(text(f"ALTER TABLE {table} DROP INDEX uq_version_wecom_event"))
                logger.info("Schema patch applied: dropped uq_version_wecom_event")
            await conn.execute(text(f"ALTER TABLE {table} DROP COLUMN event_key"))
            await conn.execute(text(f"ALTER TABLE {table} MODIFY COLUMN node_key VARCHAR(64) NOT NULL"))
            if not await _index_exists(conn, table, "uq_version_wecom_node"):
                await conn.execute(
                    text(f"ALTER TABLE {table} ADD UNIQUE KEY uq_version_wecom_node (project_id, node_key)")
                )
                logger.info("Schema patch applied: uq_version_wecom_node")

        if not await _column_exists(conn, "version_status_rules", "project_id"):
            await conn.execute(
                text(
                    """
                    CREATE TABLE version_status_rules (
                        id VARCHAR(36) PRIMARY KEY,
                        project_id VARCHAR(36) NOT NULL,
                        status VARCHAR(32) NOT NULL,
                        node_keys JSON NOT NULL,
                        sort INT NOT NULL DEFAULT 0,
                        trigger_type VARCHAR(32) NOT NULL DEFAULT 'lane',
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX ix_version_status_rules_project_id (project_id),
                        CONSTRAINT fk_version_status_rules_project FOREIGN KEY (project_id) REFERENCES projects(id)
                    )
                    """
                )
            )
            logger.info("Schema patch applied: version_status_rules table")
