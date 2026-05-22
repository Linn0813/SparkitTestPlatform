"""Tests for WeCom transition rule key matching."""

import pytest

from app.services.wecom_rule_utils import (
    normalize_status_keys,
    resolve_transition_keys_from_body,
    rule_matches_transition,
    rule_transition_keys,
    validate_transition_keys,
)


class _FakeRule:
    def __init__(
        self,
        *,
        from_status_keys=None,
        to_status_keys=None,
        from_status_key=None,
        to_status_key=None,
    ):
        self.from_status_keys = from_status_keys
        self.to_status_keys = to_status_keys
        self.from_status_key = from_status_key
        self.to_status_key = to_status_key


def test_rule_transition_keys_prefers_json_arrays():
    rule = _FakeRule(from_status_keys=["a", "b"], to_status_keys=["c"], from_status_key="x")
    assert rule_transition_keys(rule) == (["a", "b"], ["c"])


def test_rule_transition_keys_fallback_to_legacy_single():
    rule = _FakeRule(from_status_key="open", to_status_key="fixed")
    assert rule_transition_keys(rule) == (["open"], ["fixed"])


def test_rule_matches_transition_cartesian():
    from_keys = ["pending", "in_progress"]
    to_keys = ["fixed"]
    assert rule_matches_transition("pending", "fixed", from_keys, to_keys)
    assert rule_matches_transition("in_progress", "fixed", from_keys, to_keys)
    assert not rule_matches_transition("pending", "in_progress", from_keys, to_keys)
    assert not rule_matches_transition("closed", "fixed", from_keys, to_keys)


def test_rule_matches_transition_rejects_same_key():
    assert not rule_matches_transition("open", "open", ["open"], ["fixed"])


def test_validate_transition_keys_rejects_overlap():
    with pytest.raises(ValueError, match="overlap"):
        validate_transition_keys(["a", "b"], ["b", "c"])


def test_resolve_transition_keys_from_body_legacy_single():
    from_keys, to_keys = resolve_transition_keys_from_body(
        from_status_keys=None,
        to_status_keys=None,
        from_status_key="a",
        to_status_key="b",
    )
    assert from_keys == ["a"]
    assert to_keys == ["b"]


def test_normalize_status_keys_dedupes_and_sorts():
    assert normalize_status_keys(["b", "a", "b"]) == ("a", "b")
