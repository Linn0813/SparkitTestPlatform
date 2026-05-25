#!/usr/bin/env python3
"""Initialize demo admin and project. No MeterSphere data import."""
import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from sqlalchemy import select

from app.core.database import async_session_factory, engine
from app.core.security import hash_password
from app.models.project import BusinessProjectRole, Project, ProjectMember
from app.models.user import User
from app.services.project_setup import ensure_project_defaults

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin123!"
ADMIN_NAME = "演示管理员"
PROJECT_NAME = "演示项目"


async def seed() -> None:
    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.email == ADMIN_EMAIL))
        if result.scalar_one_or_none():
            print(f"Seed skipped: user {ADMIN_EMAIL} already exists.")
            return

        admin = User(
            email=ADMIN_EMAIL,
            name=ADMIN_NAME,
            password_hash=hash_password(ADMIN_PASSWORD),
            is_system_admin=True,
            is_active=True,
        )
        db.add(admin)
        await db.flush()

        project = Project(name=PROJECT_NAME)
        db.add(project)
        await db.flush()

        db.add(
            ProjectMember(
                project_id=project.id,
                user_id=admin.id,
                role=BusinessProjectRole.member,
                is_project_admin=True,
            )
        )

        admin.last_project_id = project.id

        await ensure_project_defaults(project.id, db)

        await db.commit()
        print("Seed OK:")
        print(f"  Admin: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        print(f"  Proj:  {PROJECT_NAME} ({project.id})")


async def main() -> None:
    try:
        await seed()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
