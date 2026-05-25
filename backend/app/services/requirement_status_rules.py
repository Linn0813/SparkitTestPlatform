from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.requirement_status import REQUIREMENT_STATUS_KEYS
from app.constants.requirement_status_rules import (
    DEFAULT_REQUIREMENT_STATUS_RULES,
    STATUS_RULE_TRIGGERS,
    StatusRuleLike,
)
from app.models.template import RequirementStatusRule, RequirementWorkflowNodeDef
from app.services.requirement_workflow import ensure_project_workflow_defs


def rules_to_likes(rules: list[RequirementStatusRule]) -> list[StatusRuleLike]:
    return [
        StatusRuleLike(
            status=r.status,
            node_keys=tuple(r.node_keys or []),
            sort=r.sort,
            trigger_type=r.trigger_type or "lane",  # type: ignore[arg-type]
        )
        for r in sorted(rules, key=lambda x: (x.sort, x.id))
    ]


def default_status_rule_likes() -> list[StatusRuleLike]:
    return list(DEFAULT_REQUIREMENT_STATUS_RULES)


def _default_payload_from_constants() -> list[dict]:
    return [
        {
            "status": r.status,
            "node_keys": list(r.node_keys),
            "sort": r.sort,
            "trigger_type": r.trigger_type,
        }
        for r in DEFAULT_REQUIREMENT_STATUS_RULES
    ]


async def load_project_status_rules(db: AsyncSession, project_id: str) -> list[RequirementStatusRule]:
    result = await db.execute(
        select(RequirementStatusRule)
        .where(RequirementStatusRule.project_id == project_id)
        .order_by(RequirementStatusRule.sort, RequirementStatusRule.id)
    )
    return list(result.scalars().all())


async def ensure_project_status_rules(db: AsyncSession, project_id: str) -> list[RequirementStatusRule]:
    existing = await load_project_status_rules(db, project_id)
    if existing:
        return existing
    defs = await ensure_project_workflow_defs(db, project_id)
    return await replace_project_status_rules(
        db, project_id, _default_payload_from_constants(), workflow_defs=defs
    )


async def load_status_rules_for_derive(db: AsyncSession, project_id: str) -> list[StatusRuleLike]:
    rows = await load_project_status_rules(db, project_id)
    if not rows:
        rows = await ensure_project_status_rules(db, project_id)
    return rules_to_likes(rows)


def validate_status_rules_payload(
    rules: list[dict],
    *,
    workflow_defs: list[RequirementWorkflowNodeDef],
) -> list[dict]:
    if not rules:
        raise ValueError("至少配置一条状态映射规则")
    known_keys = {d.node_key for d in workflow_defs}
    normalized: list[dict] = []
    for i, raw in enumerate(rules):
        status = (raw.get("status") or "").strip()
        if status not in REQUIREMENT_STATUS_KEYS:
            raise ValueError(f"第 {i + 1} 条规则的状态无效：{status}")
        trigger_type = (raw.get("trigger_type") or "lane").strip()
        if trigger_type not in STATUS_RULE_TRIGGERS:
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


async def replace_project_status_rules(
    db: AsyncSession,
    project_id: str,
    rules: list[dict],
    *,
    workflow_defs: list[RequirementWorkflowNodeDef],
) -> list[RequirementStatusRule]:
    payload = validate_status_rules_payload(rules, workflow_defs=workflow_defs)
    existing = await load_project_status_rules(db, project_id)
    for row in existing:
        await db.delete(row)
    await db.flush()
    rows: list[RequirementStatusRule] = []
    for item in payload:
        row = RequirementStatusRule(project_id=project_id, **item)
        db.add(row)
        rows.append(row)
    await db.flush()
    return rows
