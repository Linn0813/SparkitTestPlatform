#!/usr/bin/env python3
"""Create plan_case_result_comments table and migrate legacy result comments."""
from __future__ import annotations

import asyncio
import sys
import uuid
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
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'plan_case_result_comments'"
            )
        )
        if cols.first() is None:
            await conn.execute(
                text(
                    """
                    CREATE TABLE plan_case_result_comments (
                        id VARCHAR(36) NOT NULL PRIMARY KEY,
                        plan_case_id VARCHAR(36) NOT NULL,
                        user_id VARCHAR(36) NOT NULL,
                        body TEXT NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        INDEX ix_plan_case_result_comments_plan_case_id (plan_case_id),
                        CONSTRAINT fk_plan_case_result_comments_plan_case
                            FOREIGN KEY (plan_case_id) REFERENCES plan_cases(id),
                        CONSTRAINT fk_plan_case_result_comments_user
                            FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                    """
                )
            )

        legacy_rows = await conn.execute(
            text(
                """
                SELECT plan_case_id, executor_id, comment, executed_at
                FROM plan_case_results
                WHERE comment IS NOT NULL AND TRIM(comment) != ''
                """
            )
        )
        for row in legacy_rows.all():
            plan_case_id, executor_id, comment, executed_at = row
            exists = await conn.execute(
                text(
                    "SELECT 1 FROM plan_case_result_comments "
                    "WHERE plan_case_id = :plan_case_id LIMIT 1"
                ),
                {"plan_case_id": plan_case_id},
            )
            if exists.first() is not None:
                continue
            user_id = executor_id
            if not user_id:
                fallback = await conn.execute(text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1"))
                fallback_row = fallback.first()
                if fallback_row is None:
                    continue
                user_id = fallback_row[0]
            created_at = executed_at or "1970-01-01 00:00:00"
            await conn.execute(
                text(
                    """
                    INSERT INTO plan_case_result_comments (id, plan_case_id, user_id, body, created_at)
                    VALUES (:id, :plan_case_id, :user_id, :body, :created_at)
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "plan_case_id": plan_case_id,
                    "user_id": user_id,
                    "body": comment,
                    "created_at": created_at,
                },
            )
    await engine.dispose()
    print("Migration plan_case_result_comments complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
