from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_version import ProjectVersion
from app.models.version_workflow import VersionNodeProgress
from app.schemas.version import ProjectVersionOut, VersionNodeProgressOut, VersionWorkflowNodeDefOut
from app.services.version_workflow_defs import load_project_version_workflow_defs
from app.services.version_workflow import sort_nodes_by_defs


def version_node_out(row: VersionNodeProgress) -> VersionNodeProgressOut:
    return VersionNodeProgressOut(
        node_key=row.node_key,
        state=row.state,  # type: ignore[arg-type]
        completed_at=row.completed_at,
        operator_id=row.operator_id,
        assignee_id=row.assignee_id,
        scheduled_start=row.scheduled_start,
        scheduled_end=row.scheduled_end,
    )


async def load_version_nodes_ordered(
    db: AsyncSession, version: ProjectVersion
) -> list[VersionNodeProgress]:
    from app.services.version_workflow import load_version_nodes

    defs = await load_project_version_workflow_defs(db, version.project_id, version.version_type)
    nodes = await load_version_nodes(db, version.id)
    return sort_nodes_by_defs(list(nodes.values()), defs)


async def version_to_out(db: AsyncSession, version: ProjectVersion) -> ProjectVersionOut:
    defs = await load_project_version_workflow_defs(db, version.project_id, version.version_type)
    nodes = await load_version_nodes_ordered(db, version)
    return ProjectVersionOut(
        id=version.id,
        project_id=version.project_id,
        num=version.num,
        name=version.name,
        version_type=version.version_type,  # type: ignore[arg-type]
        status=version.status,  # type: ignore[arg-type]
        released_at=version.released_at,
        created_by=version.created_by,
        created_at=version.created_at,
        updated_at=version.updated_at,
        nodes=[version_node_out(n) for n in nodes],
        workflow_defs=[VersionWorkflowNodeDefOut.model_validate(d) for d in defs],
    )
