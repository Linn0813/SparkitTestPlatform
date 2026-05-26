from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.requirement import Requirement, RequirementNodeProgress
from app.models.template import RequirementWorkflowNodeDef
from app.services.requirement_config import ensure_project_role_defs, load_project_role_defs


def normalize_selected_role_keys(raw: list | None, *, allowed: set[str]) -> list[str]:
    if not isinstance(raw, list):
        return []
    seen: set[str] = set()
    out: list[str] = []
    for item in raw:
        key = str(item).strip()
        if not key or key not in allowed or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


async def validate_selected_role_keys(
    db: AsyncSession, project_id: str, keys: list[str] | None
) -> list[str]:
    role_defs = await load_project_role_defs(db, project_id)
    if not role_defs:
        role_defs = await ensure_project_role_defs(db, project_id)
    allowed = {r.role_key for r in role_defs}
    normalized = normalize_selected_role_keys(keys, allowed=allowed)
    unknown = [k for k in (keys or []) if str(k).strip() and str(k).strip() not in allowed]
    if unknown:
        raise ValueError(f"未知角色：{', '.join(unknown)}")
    return normalized


async def default_selected_role_keys_for_project(db: AsyncSession, project_id: str) -> list[str]:
    role_defs = await ensure_project_role_defs(db, project_id)
    return [r.role_key for r in role_defs]


async def infer_selected_role_keys_from_requirement(
    db: AsyncSession, row: Requirement
) -> list[str]:
    """从已启用节点推断（兼容旧数据回填）。"""
    defs_result = await db.execute(
        select(RequirementWorkflowNodeDef).where(
            RequirementWorkflowNodeDef.project_id == row.project_id
        )
    )
    defs_by_key = {d.node_key: d for d in defs_result.scalars().all()}
    progress_result = await db.execute(
        select(RequirementNodeProgress).where(RequirementNodeProgress.requirement_id == row.id)
    )
    keys: list[str] = []
    seen: set[str] = set()
    for prog in progress_result.scalars().all():
        if not prog.enabled:
            continue
        def_row = defs_by_key.get(prog.node_key)
        if not def_row:
            continue
        role_keys = def_row.role_keys if isinstance(def_row.role_keys, list) else []
        for rk in role_keys:
            if rk and rk not in seen:
                seen.add(rk)
                keys.append(rk)
    if keys:
        return keys
    return await default_selected_role_keys_for_project(db, row.project_id)


def read_selected_role_keys(row: Requirement) -> list | None:
    raw = getattr(row, "selected_role_keys", None)
    if raw is None:
        return None
    return raw if isinstance(raw, list) else []


async def resolve_selected_role_keys(
    db: AsyncSession, row: Requirement
) -> list[str]:
    raw = read_selected_role_keys(row)
    role_defs = await load_project_role_defs(db, row.project_id)
    if not role_defs:
        role_defs = await ensure_project_role_defs(db, row.project_id)
    allowed = {r.role_key for r in role_defs}
    if raw is None or (isinstance(raw, list) and len(raw) == 0):
        inferred = await infer_selected_role_keys_from_requirement(db, row)
        return normalize_selected_role_keys(inferred, allowed=allowed)
    return normalize_selected_role_keys(raw, allowed=allowed)


async def backfill_requirement_selected_role_keys(db: AsyncSession) -> int:
    """为 selected_role_keys 为空的需求回填。"""
    result = await db.execute(select(Requirement))
    updated = 0
    for row in result.scalars().all():
        raw = read_selected_role_keys(row)
        if raw is not None and isinstance(raw, list) and len(raw) > 0:
            continue
        row.selected_role_keys = await infer_selected_role_keys_from_requirement(db, row)
        updated += 1
    if updated:
        await db.flush()
    return updated
