#!/usr/bin/env python3
"""Migrate project_members.roles JSON -> role + is_project_admin.

Also normalizes legacy single-column role values (project_admin, viewer, etc.)
so SQLAlchemy BusinessProjectRole enum can load rows without LookupError.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text

from app.core.database import engine
from app.models import *  # noqa: F401, F403
from app.core.database import Base

_BUSINESS = ("tester", "product", "developer", "member")
_VALID_ROLES = set(_BUSINESS)


async def _column_names(conn) -> set[str]:
    rows = await conn.execute(text("SHOW COLUMNS FROM project_members"))
    return {row[0] for row in rows.all()}


async def _normalize_role_column(conn) -> None:
    """Map legacy role strings to is_project_admin + BusinessProjectRole."""
    rows = await conn.execute(text("SELECT id, role, is_project_admin FROM project_members"))
    for row_id, role_raw, is_admin in rows.all():
        role = str(role_raw or "member").strip()
        admin = bool(is_admin)

        if role == "project_admin":
            admin = True
            role = "member"
        elif role == "viewer":
            role = "member"
        elif role not in _VALID_ROLES:
            role = "member"

        await conn.execute(
            text(
                "UPDATE project_members SET role = :role, is_project_admin = :is_admin WHERE id = :id"
            ),
            {"role": role, "is_admin": int(admin), "id": row_id},
        )

    await conn.execute(
        text(
            "ALTER TABLE project_members MODIFY COLUMN role "
            "ENUM('member','tester','product','developer') NOT NULL DEFAULT 'member'"
        )
    )


async def migrate() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        cols = await _column_names(conn)

        if "role" not in cols:
            try:
                await conn.execute(
                    text(
                        "ALTER TABLE project_members ADD COLUMN role "
                        "ENUM('member','tester','product','developer') NOT NULL DEFAULT 'member'"
                    )
                )
            except Exception:
                pass
            cols = await _column_names(conn)

        if "is_project_admin" not in cols:
            try:
                await conn.execute(
                    text(
                        "ALTER TABLE project_members ADD COLUMN is_project_admin "
                        "BOOLEAN NOT NULL DEFAULT FALSE"
                    )
                )
            except Exception:
                pass
            cols = await _column_names(conn)

        if "roles" in cols:
            rows = await conn.execute(text("SELECT id, roles FROM project_members"))
            for row_id, roles_raw in rows.all():
                roles: list[str] = []
                if roles_raw:
                    if isinstance(roles_raw, str):
                        try:
                            roles = json.loads(roles_raw)
                        except json.JSONDecodeError:
                            roles = []
                    elif isinstance(roles_raw, list):
                        roles = [str(x) for x in roles_raw]
                is_admin = 1 if "project_admin" in roles else 0
                business = "member"
                for key in _BUSINESS:
                    if key in roles:
                        business = key
                        break
                await conn.execute(
                    text(
                        "UPDATE project_members SET role = :role, is_project_admin = :is_admin WHERE id = :id"
                    ),
                    {"role": business, "is_admin": is_admin, "id": row_id},
                )
            try:
                await conn.execute(text("ALTER TABLE project_members DROP COLUMN roles"))
            except Exception:
                pass

        if "role" in await _column_names(conn):
            await _normalize_role_column(conn)

    await engine.dispose()
    print("migrate_project_member_split: done")


if __name__ == "__main__":
    asyncio.run(migrate())
