#!/usr/bin/env python3
"""Create version_status_rules table and seed defaults for existing projects."""
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
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS version_status_rules (
                        id VARCHAR(36) PRIMARY KEY,
                        project_id VARCHAR(36) NOT NULL,
                        version_type VARCHAR(32) NOT NULL DEFAULT 'app_release',
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
        except Exception:
            pass

    from app.core.database import async_session_factory
    from app.services.version_status_rules import ensure_all_version_status_rules
    from app.services.version_workflow_defs import ensure_project_version_workflow_defs

    project_ids: list[str] = []
    async with async_session_factory() as db:
        result = await db.execute(text("SELECT id FROM projects"))
        project_ids = [row[0] for row in result.fetchall()]
        for pid in project_ids:
            await ensure_project_version_workflow_defs(db, pid)
            await ensure_all_version_status_rules(db, pid)
        await db.commit()

    await engine.dispose()
    print(f"Migration version_status_rules complete ({len(project_ids)} projects).")


if __name__ == "__main__":
    asyncio.run(migrate())
