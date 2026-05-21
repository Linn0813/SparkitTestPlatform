from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.file_storage import get_file_by_key, read_file_bytes, verify_download_signature

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/raw")
async def download_file_raw(
    object_key: str = Query(..., min_length=1),
    expires: int = Query(...),
    signature: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
):
    if not verify_download_signature(object_key, expires, signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired file link")
    row = await get_file_by_key(db, object_key)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    legacy_content = getattr(row, "content", None)
    body = await read_file_bytes(object_key, legacy_content)
    if body is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return Response(
        content=body,
        media_type=row.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'inline; filename="{row.filename}"',
            "Cache-Control": "private, max-age=3600",
        },
    )
