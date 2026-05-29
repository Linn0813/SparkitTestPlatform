"""Tests for case module path and list ordering helpers."""

from __future__ import annotations

from sqlalchemy import select

from app.models.case import CaseModule, TestCase
from app.services.case_module_paths import (
    apply_case_list_order,
    build_module_path_map,
    build_module_tree_order,
)


def _mod(mid: str, name: str, parent_id: str | None = None, sort: int = 0) -> CaseModule:
    m = CaseModule(project_id="p", name=name, parent_id=parent_id, sort=sort)
    m.id = mid
    return m


def test_build_module_tree_order_dfs_preorder():
    a = _mod("a", "父A")
    a1 = _mod("a1", "子A1", parent_id="a")
    a2 = _mod("a2", "子A2", parent_id="a")
    b = _mod("b", "父B", sort=1)
    b1 = _mod("b1", "子B1", parent_id="b")
    order = build_module_tree_order([a, a1, a2, b, b1])
    assert [order[mid] for mid in ("a", "a1", "a2", "b", "b1")] == [0, 1, 2, 3, 4]


def test_build_module_tree_order_sibling_sort_field():
    first = _mod("m1", "模块一", sort=0)
    second = _mod("m2", "模块二", sort=1)
    order = build_module_tree_order([second, first])
    assert order["m1"] < order["m2"]


def test_build_module_tree_order_sibling_name_tiebreak():
    beta = _mod("b", "Beta", sort=0)
    alpha = _mod("a", "Alpha", sort=0)
    order = build_module_tree_order([beta, alpha])
    assert order["a"] < order["b"]


def test_build_module_path_map():
    a = _mod("a", "父")
    b = _mod("b", "子", parent_id="a")
    paths = build_module_path_map([a, b])
    assert paths["a"] == "父"
    assert paths["b"] == "父-子"


def test_apply_case_list_order_compiles_module_rank_and_title():
    a = _mod("a", "父")
    b = _mod("b", "子", parent_id="a")
    stmt = apply_case_list_order(
        select(TestCase).where(TestCase.project_id == "p"),
        [a, b],
    )
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "CASE" in compiled.upper()
    assert "title" in compiled.lower()
    assert "a" in compiled
    assert "b" in compiled
