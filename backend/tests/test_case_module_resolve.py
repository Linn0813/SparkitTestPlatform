"""Tests for import module path parsing and resolution."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.models.case import CaseModule
from app.services.case_module_resolve import (
    UNCATEGORIZED_MODULE_NAME,
    ImportModuleResolver,
    module_name_path,
    parse_module_path_segments,
)


def test_parse_module_path_segments():
    assert parse_module_path_segments("") == []
    assert parse_module_path_segments("子A") == ["子A"]
    assert parse_module_path_segments("父-子") == ["父", "子"]
    assert parse_module_path_segments("父/子") == ["父", "子"]
    assert parse_module_path_segments("/父\\子") == ["父", "子"]


def test_module_name_path():
    a = CaseModule(project_id="p", name="A", parent_id=None, sort=0)
    a.id = "a"
    b = CaseModule(project_id="p", name="B", parent_id="a", sort=0)
    b.id = "b"
    assert module_name_path([a, b], "b") == ["A", "B"]


def _mock_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()

    async def flush():
        for call in db.add.call_args_list:
            mod = call[0][0]
            if isinstance(mod, CaseModule) and not mod.id:
                mod.id = f"new-{mod.name}"

    db.flush = flush
    db.refresh = AsyncMock()
    return db


def test_resolver_empty_uses_uncategorized():
    db = _mock_db()
    resolver = ImportModuleResolver(modules=[], project_id="p1", db=db)
    mid, err = asyncio.run(resolver.resolve(""))
    assert err is None
    assert mid is not None
    unc = next(m for m in resolver.modules if m.name == UNCATEGORIZED_MODULE_NAME)
    assert mid == unc.id
    assert unc.parent_id is None


def test_resolver_creates_path_from_root():
    db = _mock_db()
    resolver = ImportModuleResolver(modules=[], project_id="p1", db=db)
    mid, err = asyncio.run(resolver.resolve("A-B"))
    assert err is None
    a = next(m for m in resolver.modules if m.name == "A")
    b = next(m for m in resolver.modules if m.name == "B")
    assert mid == b.id
    assert b.parent_id == a.id
    assert a.parent_id is None


def test_resolver_matches_existing_path():
    db = _mock_db()
    a = CaseModule(project_id="p1", name="A", parent_id=None, sort=0)
    a.id = "a"
    b = CaseModule(project_id="p1", name="B", parent_id="a", sort=0)
    b.id = "b"
    resolver = ImportModuleResolver(modules=[a, b], project_id="p1", db=db)
    mid, err = asyncio.run(resolver.resolve("A-B"))
    assert err is None
    assert mid == "b"
    assert len(resolver.modules) == 2
