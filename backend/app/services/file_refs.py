from __future__ import annotations

import re
from typing import Any

SPARKIT_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(sparkit:([^)]+)\)")


def extract_sparkit_keys_from_text(text: str | None) -> set[str]:
    if not text:
        return set()
    return set(SPARKIT_IMAGE_RE.findall(text))


def extract_sparkit_keys_from_value(value: Any) -> set[str]:
    keys: set[str] = set()
    if value is None:
        return keys
    if isinstance(value, str):
        keys.update(extract_sparkit_keys_from_text(value))
    elif isinstance(value, dict):
        keys.update(extract_sparkit_keys_from_text(value.get("text")))
        files = value.get("files")
        if isinstance(files, list):
            for item in files:
                if isinstance(item, dict):
                    key = item.get("object_key")
                    if isinstance(key, str) and key:
                        keys.add(key)
    return keys


def extract_sparkit_keys_from_custom_fields(custom_fields: dict | None) -> set[str]:
    if not custom_fields:
        return set()
    keys: set[str] = set()
    for value in custom_fields.values():
        keys.update(extract_sparkit_keys_from_value(value))
    return keys


def file_keys_from_bug(bug) -> set[str]:
    keys = extract_sparkit_keys_from_text(getattr(bug, "description", None))
    keys.update(extract_sparkit_keys_from_custom_fields(getattr(bug, "custom_fields", None)))
    return keys


def file_keys_from_case(case) -> set[str]:
    keys = extract_sparkit_keys_from_text(getattr(case, "precondition", None))
    keys.update(extract_sparkit_keys_from_text(getattr(case, "step_text", None)))
    keys.update(extract_sparkit_keys_from_text(getattr(case, "expected_result", None)))
    keys.update(extract_sparkit_keys_from_custom_fields(getattr(case, "custom_fields", None)))
    return keys


def file_keys_from_comment_body(body: str | None) -> set[str]:
    return extract_sparkit_keys_from_text(body)
