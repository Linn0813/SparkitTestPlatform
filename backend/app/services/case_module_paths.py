from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import CaseModule


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
