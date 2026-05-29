from __future__ import annotations

from typing import Optional

from sqlalchemy import Select, case as sa_case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import CaseModule, TestCase


async def load_project_modules(db: AsyncSession, project_id: str) -> list[CaseModule]:
    result = await db.execute(
        select(CaseModule).where(CaseModule.project_id == project_id).order_by(CaseModule.sort, CaseModule.name)
    )
    return list(result.scalars().all())


def build_module_path_map(modules: list[CaseModule]) -> dict[str, str]:
    by_id = {m.id: m for m in modules}

    def path_for(module_id: str) -> str:
        parts: list[str] = []
        cur: Optional[str] = module_id
        seen: set[str] = set()
        while cur and cur not in seen:
            seen.add(cur)
            mod = by_id.get(cur)
            if not mod:
                break
            parts.append(mod.name)
            cur = mod.parent_id
        parts.reverse()
        return "-".join(parts)

    return {m.id: path_for(m.id) for m in modules}


def build_module_tree_order(modules: list[CaseModule]) -> dict[str, int]:
    """DFS 先序为每个 module_id 分配序号，同级按 (sort, name) 排序。"""
    by_parent: dict[str | None, list[CaseModule]] = {}
    for m in modules:
        by_parent.setdefault(m.parent_id, []).append(m)
    for siblings in by_parent.values():
        siblings.sort(key=lambda m: (m.sort, m.name))

    order: dict[str, int] = {}
    idx = 0

    def walk(parent_id: str | None) -> None:
        nonlocal idx
        for m in by_parent.get(parent_id, []):
            order[m.id] = idx
            idx += 1
            walk(m.id)

    walk(None)
    return order


def apply_case_list_order(stmt: Select, modules: list[CaseModule]) -> Select:
    order_map = build_module_tree_order(modules)
    module_rank = sa_case(order_map, value=TestCase.module_id, else_=len(order_map))
    return stmt.order_by(module_rank, TestCase.title.asc())
