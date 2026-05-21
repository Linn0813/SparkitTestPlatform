from __future__ import annotations

import re
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import CaseModule

MODULE_PATH_SEP = "-"
_PATH_SPLITTERS_RE = re.compile(r"[/\\>|]+")
UNCATEGORIZED_MODULE_NAME = "未分类"


def parse_module_path_segments(raw: str) -> list[str]:
    """将 Excel「模块」单元格解析为各级模块名。"""
    text = (raw or "").strip().strip("/\\")
    if not text:
        return []
    if _PATH_SPLITTERS_RE.search(text):
        return [p.strip() for p in _PATH_SPLITTERS_RE.split(text) if p.strip()]
    return [p.strip() for p in text.split(MODULE_PATH_SEP) if p.strip()]


def module_name_path(modules: list[CaseModule], module_id: str) -> list[str]:
    by_id = {m.id: m for m in modules}
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
    return parts


class ImportModuleResolver:
    """导入时解析模块路径：空列归入「未分类」，有值则从项目根匹配或自动创建。"""

    def __init__(
        self,
        *,
        modules: list[CaseModule],
        project_id: str,
        db: AsyncSession,
    ) -> None:
        self.modules = modules
        self.project_id = project_id
        self.db = db
        self._cache: dict[str, str] = {}
        self._uncategorized_id: str | None = None
        self._by_parent: dict[str | None, list[CaseModule]] = {}
        self._reindex()

    def _reindex(self) -> None:
        self._by_parent = {}
        for m in self.modules:
            pid = m.parent_id
            self._by_parent.setdefault(pid, []).append(m)

    def _find_child(self, parent_id: str | None, name: str) -> CaseModule | None:
        for m in self._by_parent.get(parent_id, []):
            if m.name == name:
                return m
        return None

    async def _create_child(self, parent_id: str | None, name: str) -> CaseModule:
        siblings = self._by_parent.get(parent_id, [])
        mod = CaseModule(
            project_id=self.project_id,
            name=name,
            parent_id=parent_id,
            sort=len(siblings),
        )
        self.db.add(mod)
        await self.db.flush()
        await self.db.refresh(mod)
        self.modules.append(mod)
        self._reindex()
        return mod

    async def _ensure_uncategorized_module(self) -> str:
        if self._uncategorized_id:
            return self._uncategorized_id
        existing = self._find_child(None, UNCATEGORIZED_MODULE_NAME)
        if existing:
            self._uncategorized_id = existing.id
            return existing.id
        mod = await self._create_child(None, UNCATEGORIZED_MODULE_NAME)
        self._uncategorized_id = mod.id
        return mod.id

    async def _walk(
        self,
        segments: list[str],
        *,
        start_parent_id: str | None,
        create: bool,
    ) -> tuple[str | None, Optional[str]]:
        parent_id = start_parent_id
        for seg in segments:
            child = self._find_child(parent_id, seg)
            if not child:
                if not create:
                    return None, None
                child = await self._create_child(parent_id, seg)
            parent_id = child.id
        return parent_id, None

    async def resolve(self, path_raw: str) -> tuple[str | None, Optional[str]]:
        key = (path_raw or "").strip() or "__uncategorized__"
        if key in self._cache:
            return self._cache[key], None

        segments = parse_module_path_segments(path_raw)
        if not segments:
            mid = await self._ensure_uncategorized_module()
            self._cache[key] = mid
            return mid, None

        found, _ = await self._walk(segments, start_parent_id=None, create=False)
        if found:
            self._cache[key] = found
            return found, None

        created, _ = await self._walk(segments, start_parent_id=None, create=True)
        assert created
        self._cache[key] = created
        return created, None
