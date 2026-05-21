from __future__ import annotations

from fastapi import HTTPException, status

from app.schemas.template import TemplateFieldSchema

ALLOWED_FIELD_TYPES = frozenset({
    "text",
    "textarea",  # 历史数据兼容，与 text 等价
    "richtext",
    "number",
    "date",
    "switch",
    "select",
    "multi_select",
    "member",
})
OPTION_FIELD_TYPES = frozenset({"select", "multi_select"})

# 与前端 schemas/entityFieldSchema.ts RESERVED_TEMPLATE_FIELD_NAMES 保持一致
RESERVED_FIELD_NAMES_BY_SCENE: dict[str, frozenset[str]] = {
    "bug": frozenset({
        "缺陷标题",
        "标题",
        "状态",
        "提出人",
        "跟进人",
        "描述",
        "附件",
        "关联需求",
        "关联测试计划",
        "规划迭代",
        "发现版本",
        "关联计划",
    }),
    "functional_case": frozenset({
        "用例标题",
        "标题",
        "模块",
        "优先级",
        "前置条件",
        "步骤",
        "预期结果",
        "关联需求",
    }),
}


def validate_template_fields(fields: list, *, scene: str | None = None) -> list[dict]:
    if not isinstance(fields, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="fields must be a list")
    seen_ids: set[str] = set()
    normalized: list[dict] = []
    for i, raw in enumerate(fields):
        try:
            item = TemplateFieldSchema.model_validate(raw)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid field at index {i}: {e}",
            ) from e
        if item.type not in ALLOWED_FIELD_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported field type: {item.type}",
            )
        if item.id in seen_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Duplicate field id: {item.id}")
        seen_ids.add(item.id)
        if item.type in OPTION_FIELD_TYPES and not item.options:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"选项类字段「{item.name}」至少需要一个选项",
            )
        if scene:
            reserved = RESERVED_FIELD_NAMES_BY_SCENE.get(scene)
            if reserved and item.name.strip() in reserved:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"字段名「{item.name}」与系统字段重复，请改名",
                )
        normalized.append({**item.model_dump(), "sort": item.sort if item.sort else i})
    normalized.sort(key=lambda x: x["sort"])
    for i, f in enumerate(normalized):
        f["sort"] = i
    return normalized
