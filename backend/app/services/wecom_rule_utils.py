from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.wecom_rule import BugWecomNotifyRule


def rule_transition_keys(rule: BugWecomNotifyRule) -> tuple[list[str], list[str]]:
    """JSON 数组优先，兼容旧单值字段。"""
    from_keys: list[str] = []
    to_keys: list[str] = []
    if isinstance(rule.from_status_keys, list):
        from_keys = [k for k in rule.from_status_keys if k]
    if isinstance(rule.to_status_keys, list):
        to_keys = [k for k in rule.to_status_keys if k]
    if not from_keys and rule.from_status_key:
        from_keys = [rule.from_status_key]
    if not to_keys and rule.to_status_key:
        to_keys = [rule.to_status_key]
    return from_keys, to_keys


def normalize_status_keys(keys: list[str]) -> tuple[str, ...]:
    return tuple(sorted({k.strip() for k in keys if k and str(k).strip()}))


def keys_signature(from_keys: list[str], to_keys: list[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return normalize_status_keys(from_keys), normalize_status_keys(to_keys)


def validate_transition_keys(from_keys: list[str], to_keys: list[str]) -> None:
    from_norm = normalize_status_keys(from_keys)
    to_norm = normalize_status_keys(to_keys)
    if not from_norm or not to_norm:
        raise ValueError("from_status_keys and to_status_keys required for transition rules")
    overlap = set(from_norm) & set(to_norm)
    if overlap:
        raise ValueError("from and to status must not overlap")


def rule_matches_transition(from_key: str, to_key: str, from_keys: list[str], to_keys: list[str]) -> bool:
    if not from_key or not to_key or from_key == to_key:
        return False
    from_norm = normalize_status_keys(from_keys)
    to_norm = normalize_status_keys(to_keys)
    return from_key in from_norm and to_key in to_norm


def resolve_transition_keys_from_body(
    *,
    from_status_keys: list[str] | None,
    to_status_keys: list[str] | None,
    from_status_key: str | None = None,
    to_status_key: str | None = None,
) -> tuple[list[str], list[str]]:
    from_keys = list(from_status_keys or [])
    to_keys = list(to_status_keys or [])
    if not from_keys and from_status_key:
        from_keys = [from_status_key]
    if not to_keys and to_status_key:
        to_keys = [to_status_key]
    validate_transition_keys(from_keys, to_keys)
    return list(normalize_status_keys(from_keys)), list(normalize_status_keys(to_keys))
