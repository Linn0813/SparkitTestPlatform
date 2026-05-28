from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.version_nodes import VERSION_NODE_KEYS
from app.models.project_version import ProjectVersion
from app.models.version_workflow import VersionNodeProgress, VersionNodeState
from app.schemas.version import ProjectVersionOut, VersionNodeProgressOut


async def load_version_nodes_ordered(
    db: AsyncSession, version_id: str
) -> list[VersionNodeProgress]:
    result = await db.execute(
        select(VersionNodeProgress).where(VersionNodeProgress.version_id == version_id)
    )
    by_key = {row.node_key: row for row in result.scalars().all()}
    return [by_key[key] for key in VERSION_NODE_KEYS if key in by_key]


def version_node_out(row: VersionNodeProgress) -> VersionNodeProgressOut:
    return VersionNodeProgressOut(
        node_key=row.node_key,  # type: ignore[arg-type]
        state=row.state,  # type: ignore[arg-type]
        completed_at=row.completed_at,
        operator_id=row.operator_id,
    )


async def version_to_out(db: AsyncSession, version: ProjectVersion) -> ProjectVersionOut:
    nodes = await load_version_nodes_ordered(db, version.id)
    return ProjectVersionOut(
        id=version.id,
        project_id=version.project_id,
        num=version.num,
        name=version.name,
        status=version.status,  # type: ignore[arg-type]
        released_at=version.released_at,
        created_by=version.created_by,
        created_at=version.created_at,
        updated_at=version.updated_at,
        nodes=[version_node_out(n) for n in nodes],
    )
