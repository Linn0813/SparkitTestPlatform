from __future__ import annotations

from fastapi import HTTPException, status

OPTION_FIELD_TYPES = frozenset({"select", "multi_select"})


def _is_empty_required(val, field_type: str) -> bool:
    if val is None:
        return True
    if field_type == "multi_select":
        return not isinstance(val, list) or len(val) == 0
    if field_type == "switch":
        return False
    if field_type == "member":
        return not isinstance(val, str) or not val.strip()
    if field_type == "richtext":
        if not isinstance(val, dict):
            return True
        text = val.get("text") or ""
        files = val.get("files") or []
        return (not str(text).strip()) and (not isinstance(files, list) or len(files) == 0)
    if field_type == "number":
        return val == ""
    if isinstance(val, str):
        return not val.strip()
    return val == ""


def _validate_richtext(val, field_name: str, project_id: str | None) -> None:
    if not isinstance(val, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Field {field_name} must be rich text object",
        )
    text = val.get("text", "")
    if text is not None and not isinstance(text, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Field {field_name} text must be string",
        )
    files = val.get("files", [])
    if not isinstance(files, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Field {field_name} files must be a list",
        )
    prefix = f"projects/{project_id}/" if project_id else None
    for item in files:
        if not isinstance(item, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file entry in {field_name}",
            )
        key = item.get("object_key")
        if not key or not isinstance(key, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file key in {field_name}",
            )
        if prefix and not key.startswith(prefix):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File not in project scope: {field_name}",
            )
        kind = item.get("kind", "file")
        if kind not in ("image", "video", "file"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file kind in {field_name}",
            )


def validate_custom_fields(
    fields_schema: list,
    custom_fields: dict,
    *,
    project_id: str | None = None,
    project_member_ids: set[str] | None = None,
) -> dict:
    if custom_fields is None:
        custom_fields = {}
    allowed_ids = {f["id"] for f in fields_schema}
    for key in custom_fields:
        if key not in allowed_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown field: {key}")
    for field in fields_schema:
        fid = field["id"]
        ftype = field.get("type") or "text"
        if field.get("required"):
            val = custom_fields.get(fid)
            if _is_empty_required(val, ftype):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Field required: {field.get('name', fid)}",
                )
        if fid not in custom_fields:
            continue
        val = custom_fields[fid]
        if val is None or val == "":
            continue
        opts = field.get("options") or []
        if ftype == "select" and opts and val not in opts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid option for {field.get('name', fid)}",
            )
        if ftype == "multi_select":
            if not isinstance(val, list):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Field {field.get('name', fid)} must be a list",
                )
            if opts:
                for item in val:
                    if item not in opts:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid option for {field.get('name', fid)}",
                        )
        if ftype == "number" and not isinstance(val, (int, float)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Field {field.get('name', fid)} must be a number",
            )
        if ftype == "switch" and not isinstance(val, bool):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Field {field.get('name', fid)} must be boolean",
            )
        if ftype == "member":
            if not isinstance(val, str) or not val.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Field {field.get('name', fid)} must be user id",
                )
            if project_member_ids is not None and val not in project_member_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid member for {field.get('name', fid)}",
                )
        if ftype == "richtext":
            _validate_richtext(val, field.get("name", fid), project_id)
    return custom_fields


async def load_project_member_user_ids(db, project_id: str) -> set[str]:
    from sqlalchemy import select

    from app.models.project import ProjectMember

    result = await db.execute(select(ProjectMember.user_id).where(ProjectMember.project_id == project_id))
    return set(result.scalars().all())
