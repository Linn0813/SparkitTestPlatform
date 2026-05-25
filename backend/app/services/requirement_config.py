from __future__ import annotations

import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.requirement_nodes import REQUIREMENT_ROLE_KEYS, REQUIREMENT_ROLE_LABELS
from app.models.requirement import Requirement
from app.models.template import RequirementOptionDef, RequirementRoleDef, RequirementWorkflowNodeDef

ROLE_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
OPTION_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
OPTION_CATEGORIES = frozenset({"priority", "req_type"})

DEFAULT_OPTIONS: list[tuple[str, str, str, int]] = [
    ("priority", "p00", "P00", 0),
    ("priority", "p0", "P0", 1),
    ("priority", "p1", "P1", 2),
    ("req_type", "feature", "需求开发", 0),
    ("req_type", "tech_optimization", "技术优化", 1),
]


def validate_role_key_format(role_key: str) -> None:
    if not ROLE_KEY_PATTERN.match(role_key):
        raise ValueError("角色标识须为小写字母开头，仅含小写字母、数字和下划线")


def validate_option_key_format(option_key: str) -> None:
    if not OPTION_KEY_PATTERN.match(option_key):
        raise ValueError("选项标识须为小写字母开头，仅含小写字母、数字和下划线")


async def load_project_role_defs(db: AsyncSession, project_id: str) -> list[RequirementRoleDef]:
    result = await db.execute(
        select(RequirementRoleDef)
        .where(RequirementRoleDef.project_id == project_id)
        .order_by(RequirementRoleDef.sort, RequirementRoleDef.role_key)
    )
    return list(result.scalars().all())


async def ensure_project_role_defs(db: AsyncSession, project_id: str) -> list[RequirementRoleDef]:
    existing = await load_project_role_defs(db, project_id)
    if existing:
        return existing
    rows: list[RequirementRoleDef] = []
    for sort, role_key in enumerate(REQUIREMENT_ROLE_KEYS):
        row = RequirementRoleDef(
            project_id=project_id,
            role_key=role_key,
            label=REQUIREMENT_ROLE_LABELS.get(role_key, role_key),
            sort=sort,
        )
        db.add(row)
        rows.append(row)
    await db.flush()
    return rows


async def load_project_option_defs(
    db: AsyncSession, project_id: str, category: str | None = None
) -> list[RequirementOptionDef]:
    stmt = select(RequirementOptionDef).where(RequirementOptionDef.project_id == project_id)
    if category:
        stmt = stmt.where(RequirementOptionDef.category == category)
    stmt = stmt.order_by(RequirementOptionDef.category, RequirementOptionDef.sort, RequirementOptionDef.option_key)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def ensure_project_option_defs(db: AsyncSession, project_id: str) -> list[RequirementOptionDef]:
    existing = await load_project_option_defs(db, project_id)
    if existing:
        return existing
    rows: list[RequirementOptionDef] = []
    for category, option_key, label, sort in DEFAULT_OPTIONS:
        row = RequirementOptionDef(
            project_id=project_id,
            category=category,
            option_key=option_key,
            label=label,
            sort=sort,
        )
        db.add(row)
        rows.append(row)
    await db.flush()
    return rows


async def load_project_role_keys(db: AsyncSession, project_id: str) -> set[str]:
    defs = await ensure_project_role_defs(db, project_id)
    return {d.role_key for d in defs}


async def validate_role_keys_for_project(
    db: AsyncSession, project_id: str, role_keys: list[str]
) -> None:
    if not role_keys:
        raise ValueError("至少选择一个角色")
    allowed = await load_project_role_keys(db, project_id)
    seen: set[str] = set()
    for role_key in role_keys:
        if role_key not in allowed:
            raise ValueError(f"无效角色: {role_key}")
        if role_key in seen:
            raise ValueError(f"角色重复: {role_key}")
        seen.add(role_key)


async def load_option_keys(db: AsyncSession, project_id: str, category: str) -> set[str]:
    defs = await ensure_project_option_defs(db, project_id)
    return {d.option_key for d in defs if d.category == category}


async def validate_requirement_option(
    db: AsyncSession, project_id: str, category: str, option_key: str
) -> None:
    allowed = await load_option_keys(db, project_id, category)
    if option_key not in allowed:
        raise ValueError(f"无效的{category}选项: {option_key}")


async def count_role_usage_in_workflow(db: AsyncSession, project_id: str, role_key: str) -> int:
    defs = await load_project_workflow_defs_for_project(db, project_id)
    count = 0
    for d in defs:
        if role_key in (d.role_keys or []):
            count += 1
    return count


async def load_project_workflow_defs_for_project(
    db: AsyncSession, project_id: str
) -> list[RequirementWorkflowNodeDef]:
    result = await db.execute(
        select(RequirementWorkflowNodeDef).where(RequirementWorkflowNodeDef.project_id == project_id)
    )
    return list(result.scalars().all())


async def count_role_usage_in_requirements(db: AsyncSession, project_id: str, role_key: str) -> int:
    result = await db.execute(select(Requirement).where(Requirement.project_id == project_id))
    count = 0
    for req in result.scalars().all():
        assignees = req.role_assignee_ids if isinstance(req.role_assignee_ids, dict) else {}
        ids = assignees.get(role_key) or []
        if ids:
            count += 1
    return count


async def count_option_usage(db: AsyncSession, project_id: str, category: str, option_key: str) -> int:
    col = Requirement.priority if category == "priority" else Requirement.req_type
    result = await db.execute(
        select(func.count()).select_from(Requirement).where(
            Requirement.project_id == project_id,
            col == option_key,
        )
    )
    return result.scalar() or 0


async def rename_role_key_in_project(
    db: AsyncSession, project_id: str, old_key: str, new_key: str
) -> None:
    defs = await load_project_workflow_defs_for_project(db, project_id)
    for d in defs:
        if old_key in (d.role_keys or []):
            d.role_keys = [new_key if k == old_key else k for k in d.role_keys]

    reqs = await db.execute(select(Requirement).where(Requirement.project_id == project_id))
    for req in reqs.scalars().all():
        assignees = dict(req.role_assignee_ids) if isinstance(req.role_assignee_ids, dict) else {}
        if old_key in assignees:
            assignees[new_key] = assignees.pop(old_key)
            req.role_assignee_ids = assignees
    await db.flush()


async def count_options_in_category(db: AsyncSession, project_id: str, category: str) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(RequirementOptionDef)
        .where(
            RequirementOptionDef.project_id == project_id,
            RequirementOptionDef.category == category,
        )
    )
    return result.scalar() or 0
