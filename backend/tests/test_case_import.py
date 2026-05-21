"""Tests for case import template columns and header matching."""

from app.services.case_import import (
    HEADER_ALIASES,
    build_import_columns,
    expected_headers,
    generate_template_workbook,
    _find_header_row_index,
    _headers_match,
    _normalize_file_headers,
)


def test_build_import_columns_includes_module_and_custom():
    schema = [
        {"id": "remark", "name": "备注", "type": "textarea", "required": False, "options": [], "sort": 1},
        {"id": "dup", "name": "用例标题", "type": "text", "required": False, "options": [], "sort": 2},
    ]
    cols = build_import_columns(schema)
    headers = expected_headers(cols)
    assert headers[0] == "模块"
    assert headers[1] == "用例标题"
    assert "备注" in headers
    assert "用例标题" not in headers[2:]  # 重复系统名不进入自定义列


def test_header_aliases_and_row_detection():
    expected = expected_headers(build_import_columns([]))
    alias_row = list(expected)
    alias_row[1] = "标题"
    rows = [("填写说明",), tuple(alias_row)]
    idx = _find_header_row_index(rows, expected)
    assert idx == 1
    assert _headers_match(_normalize_file_headers(alias_row), expected)
    assert HEADER_ALIASES["标题"] == "用例标题"


def test_generate_template_workbook_has_instruction_and_header():
    cols = build_import_columns(
        [{"id": "remark", "name": "备注", "type": "text", "required": False, "options": [], "sort": 0}]
    )
    data = generate_template_workbook(cols)
    assert len(data) > 100
    from openpyxl import load_workbook
    import io

    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    assert "填写说明" in str(rows[0][0] or "")
    assert list(rows[1])[:3] == ["模块", "用例标题", "优先级"]
    assert rows[2][1] == "示例用例标题"
