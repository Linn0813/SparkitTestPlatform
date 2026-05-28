from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.version_types import VERSION_TYPES
from app.models.version_workflow import VersionWecomNotifyRule
from app.services.version_wecom_defaults import default_template_for_node
from app.services.version_workflow_defs import load_project_version_workflow_defs


class VersionWecomRuleError(ValueError):
    pass


async def load_project_notifyable_nodes(
    db: AsyncSession,
    project_id: str,
) -> dict[str, str]:
    """合并项目各版本类型工作流节点，按 node_key 去重。"""
    by_key: dict[str, str] = {}
    for version_type in VERSION_TYPES:
        defs = await load_project_version_workflow_defs(db, project_id, version_type)
        for d in defs:
            if d.node_key not in by_key:
                by_key[d.node_key] = d.label
    return by_key


async def validate_rule_node_key(
    db: AsyncSession,
    project_id: str,
    node_key: str,
) -> str:
    nodes = await load_project_notifyable_nodes(db, project_id)
    label = nodes.get(node_key)
    if not label:
        raise VersionWecomRuleError("未知工作流节点")
    return label


async def node_label_for_rule(
    db: AsyncSession,
    project_id: str,
    node_key: str,
) -> str:
    nodes = await load_project_notifyable_nodes(db, project_id)
    return nodes.get(node_key, node_key)


async def list_version_wecom_rule_options(
    project_id: str,
    db: AsyncSession,
) -> list[dict[str, object]]:
    nodes = await load_project_notifyable_nodes(db, project_id)
    result = await db.execute(
        select(VersionWecomNotifyRule.node_key).where(
            VersionWecomNotifyRule.project_id == project_id
        )
    )
    configured = {row[0] for row in result.all()}
    options: list[dict[str, object]] = []
    for node_key, node_label in sorted(nodes.items(), key=lambda x: x[0]):
        options.append(
            {
                "node_key": node_key,
                "node_label": node_label,
                "default_message_template": default_template_for_node(node_key, node_label),
                "configured": node_key in configured,
            }
        )
    return options
