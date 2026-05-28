from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.version_status_rules import (
    VERSION_STATUS_KEYS,
    VERSION_STATUS_RULE_TRIGGERS,
    VersionStatusRuleLike,
    default_status_rules_for_type,
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


def default_version_status_rule_likes(version_type: str) -> list[VersionStatusRuleLike]:
    return list(default_status_rules_for_type(version_type))


def _default_payload_for_type(
    version_type: str,
    workflow_defs: list[VersionWorkflowNodeDef] | None = None,
) -> list[dict]:
    known_keys = {d.node_key for d in (workflow_defs or [])}
    payload: list[dict] = []
    for r in default_status_rules_for_type(version_type):
        node_keys = [k for k in r.node_keys if k in known_keys] if known_keys else list(r.node_keys)
        if r.trigger_type != "status_hold" and not node_keys:
            continue
        payload.append(
            {
                "status": r.status,
                "node_keys": node_keys,
                "sort": r.sort,
                "trigger_type": r.trigger_type,
            }
        )
    if not payload and known_keys:
        fallback_key = next(
            (k for k in ("planning", "development", "release_verification", "live") if k in known_keys),
            next(iter(sorted(known_keys))),
        )
        payload.append(
            {
                "status": "planning",
                "node_keys": [fallback_key],
                "sort": 10,
                "trigger_type": "lane",
            }
        )
    return payload


def _validate_version_type(version_type: str) -> str:
    vt = (version_type or "").strip()
    if vt not in VERSION_TYPES:
        raise ValueError(f"未知版本类型：{version_type}")
    return vt


async def load_project_version_status_rules(
    db: AsyncSession,
    project_id: str,
    version_type: str,
) -> list[VersionStatusRule]:
    vt = _validate_version_type(version_type)
    result = await db.execute(
        select(VersionStatusRule)
        .where(
            VersionStatusRule.project_id == project_id,
            VersionStatusRule.version_type == vt,
        )
        .order_by(VersionStatusRule.sort, VersionStatusRule.id)
    )
    return list(result.scalars().all())


async def ensure_project_version_status_rules(
    db: AsyncSession,
    project_id: str,
    version_type: str,
) -> list[VersionStatusRule]:
    vt = _validate_version_type(version_type)
    existing = await load_project_version_status_rules(db, project_id, vt)
    if existing:
        return existing
    await ensure_project_version_workflow_defs(db, project_id, vt)
    defs = await load_project_version_workflow_defs(db, project_id, vt)
    return await replace_project_version_status_rules(
        db, project_id, vt, _default_payload_for_type(vt, defs), workflow_defs=defs
    )


async def load_status_rules_for_derive(
    db: AsyncSession,
    project_id: str,
    version_type: str,
) -> list[VersionStatusRuleLike]:
    vt = _validate_version_type(version_type or "app_release")
    rows = await load_project_version_status_rules(db, project_id, vt)
    if not rows:
        rows = await ensure_project_version_status_rules(db, project_id, vt)
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
    version_type: str,
    rules: list[dict],
    *,
    workflow_defs: list[VersionWorkflowNodeDef],
) -> list[VersionStatusRule]:
    vt = _validate_version_type(version_type)
    payload = validate_version_status_rules_payload(rules, workflow_defs=workflow_defs)
    existing = await load_project_version_status_rules(db, project_id, vt)
    for row in existing:
        await db.delete(row)
    await db.flush()
    rows: list[VersionStatusRule] = []
    for item in payload:
        row = VersionStatusRule(project_id=project_id, version_type=vt, **item)
        db.add(row)
        rows.append(row)
    await db.flush()
    return rows


async def ensure_all_version_status_rules(
    db: AsyncSession,
    project_id: str,
) -> None:
    for version_type in VERSION_TYPES:
        await ensure_project_version_status_rules(db, project_id, version_type)
