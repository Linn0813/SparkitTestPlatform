from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.version_status_rules import (
    DEFAULT_VERSION_STATUS_RULES,
    VERSION_STATUS_KEYS,
    VERSION_STATUS_RULE_TRIGGERS,
    VersionStatusRuleLike,
)
from app.constants.version_types import VERSION_TYPES
from app.models.template import VersionStatusRule, VersionWorkflowNodeDef
from app.services.version_workflow_defs import ensure_project_version_workflow_defs, load_project_version_workflow_defs


def rules_to_likes(rules: list[VersionStatusRule]) -> list[VersionStatusRuleLike]:
    return [
        VersionStatusRuleLike(
            status=r.status,
            node_keys=tuple(r.node_keys or []),
            sort=r.sort,
            trigger_type=r.trigger_type or "lane",  # type: ignore[arg-type]
        )
        for r in sorted(rules, key=lambda x: (x.sort, x.id))
    ]


def default_version_status_rule_likes() -> list[VersionStatusRuleLike]:
    return list(DEFAULT_VERSION_STATUS_RULES)


def _default_payload_from_constants() -> list[dict]:
    return [
        {
            "status": r.status,
            "node_keys": list(r.node_keys),
            "sort": r.sort,
            "trigger_type": r.trigger_type,
        }
        for r in DEFAULT_VERSION_STATUS_RULES
    ]


async def load_all_version_workflow_defs_union(
    db: AsyncSession,
    project_id: str,
) -> list[VersionWorkflowNodeDef]:
    await ensure_project_version_workflow_defs(db, project_id)
    result: list[VersionWorkflowNodeDef] = []
    for version_type in VERSION_TYPES:
        result.extend(await load_project_version_workflow_defs(db, project_id, version_type))
    return result


async def load_project_version_status_rules(
    db: AsyncSession,
    project_id: str,
) -> list[VersionStatusRule]:
    result = await db.execute(
        select(VersionStatusRule)
        .where(VersionStatusRule.project_id == project_id)
        .order_by(VersionStatusRule.sort, VersionStatusRule.id)
    )
    return list(result.scalars().all())


async def ensure_project_version_status_rules(
    db: AsyncSession,
    project_id: str,
) -> list[VersionStatusRule]:
    existing = await load_project_version_status_rules(db, project_id)
    if existing:
        return existing
    defs = await load_all_version_workflow_defs_union(db, project_id)
    return await replace_project_version_status_rules(
        db, project_id, _default_payload_from_constants(), workflow_defs=defs
    )


async def load_status_rules_for_derive(
    db: AsyncSession,
    project_id: str,
) -> list[VersionStatusRuleLike]:
    rows = await load_project_version_status_rules(db, project_id)
    if not rows:
        rows = await ensure_project_version_status_rules(db, project_id)
    return rules_to_likes(rows)


def validate_version_status_rules_payload(
    rules: list[dict],
    *,
    workflow_defs: list[VersionWorkflowNodeDef],
) -> list[dict]:
    if not rules:
        raise ValueError("至少配置一条状态映射规则")
    known_keys = {d.node_key for d in workflow_defs}
    normalized: list[dict] = []
    for i, raw in enumerate(rules):
        status = (raw.get("status") or "").strip()
        if status not in VERSION_STATUS_KEYS:
            raise ValueError(f"第 {i + 1} 条规则的状态无效：{status}")
        trigger_type = (raw.get("trigger_type") or "lane").strip()
        if trigger_type not in VERSION_STATUS_RULE_TRIGGERS:
            raise ValueError(f"第 {i + 1} 条规则触发方式无效：{trigger_type}")
        node_keys = [str(k).strip() for k in (raw.get("node_keys") or []) if str(k).strip()]
        if trigger_type == "status_hold":
            pass
        elif not node_keys:
            raise ValueError(f"第 {i + 1} 条规则须至少关联一个节点")
        else:
            unknown = [k for k in node_keys if k not in known_keys]
            if unknown:
                raise ValueError(f"第 {i + 1} 条规则含未知节点：{', '.join(unknown)}")
        sort = int(raw.get("sort", i))
        if sort < 0:
            raise ValueError(f"第 {i + 1} 条规则优先级不能为负数")
        normalized.append(
            {
                "status": status,
                "node_keys": node_keys,
                "sort": sort,
                "trigger_type": trigger_type,
            }
        )
    return normalized


async def replace_project_version_status_rules(
    db: AsyncSession,
    project_id: str,
    rules: list[dict],
    *,
    workflow_defs: list[VersionWorkflowNodeDef],
) -> list[VersionStatusRule]:
    payload = validate_version_status_rules_payload(rules, workflow_defs=workflow_defs)
    existing = await load_project_version_status_rules(db, project_id)
    for row in existing:
        await db.delete(row)
    await db.flush()
    rows: list[VersionStatusRule] = []
    for item in payload:
        row = VersionStatusRule(project_id=project_id, **item)
        db.add(row)
        rows.append(row)
    await db.flush()
    return rows
