from __future__ import annotations

import hashlib
import hmac
import logging
import time
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services import minio_storage

logger = logging.getLogger(__name__)

_FILE_KEY_PREFIXES = ("bugs/", "projects/")


def _object_key(prefix: str, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    return f"{prefix}/{uuid.uuid4()}.{ext}"


def build_file_download_url(object_key: str, expires_seconds: int = 7 * 24 * 3600) -> str:
    """MinIO 预签名 GET，适合图片/视频直连与流式播放。"""
    return minio_storage.presigned_get_url(object_key, expires_seconds)


def verify_download_signature(object_key: str, expires: int, signature: str) -> bool:
    """兼容旧版经 API 代理的签名链接（/files/raw）。"""
    if expires < int(time.time()):
        return False
    expected = hmac.new(
        settings.secret_key.encode("utf-8"),
        f"{object_key}\n{expires}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def store_bytes(
    db: AsyncSession,
    *,
    data: bytes,
    filename: str,
    content_type: str,
    prefix: str,
) -> tuple[str, int]:
    from app.models.stored_file import StoredFile

    storage_key = _object_key(prefix, filename)
    await minio_storage.put_object(storage_key, data, content_type)
    row = StoredFile(
        storage_key=storage_key,
        filename=filename or "file.bin",
        content_type=content_type or "application/octet-stream",
        size=len(data),
    )
    db.add(row)
    await db.flush()
    return storage_key, len(data)


async def upload_bytes(
    db: AsyncSession,
    data: bytes,
    filename: str,
    content_type: str = "application/octet-stream",
) -> tuple[str, int]:
    return await store_bytes(db, data=data, filename=filename, content_type=content_type, prefix="bugs")


async def upload_project_bytes(
    db: AsyncSession,
    project_id: str,
    data: bytes,
    filename: str,
    content_type: str = "application/octet-stream",
) -> tuple[str, int]:
    return await store_bytes(
        db,
        data=data,
        filename=filename,
        content_type=content_type,
        prefix=f"projects/{project_id}",
    )


async def get_file_by_key(db: AsyncSession, storage_key: str):
    from app.models.stored_file import StoredFile

    result = await db.execute(select(StoredFile).where(StoredFile.storage_key == storage_key))
    return result.scalar_one_or_none()


async def read_file_bytes(storage_key: str, row_content: Optional[bytes] = None) -> bytes | None:
    """优先 MinIO；row_content 为迁移前留在 MySQL 的二进制（可选）。"""
    data = await minio_storage.get_object_bytes(storage_key)
    if data is not None:
        return data
    return row_content


async def delete_object_safe(db: AsyncSession, object_key: str) -> None:
    from app.models.stored_file import StoredFile

    if not object_key or not object_key.startswith(_FILE_KEY_PREFIXES):
        return
    try:
        await minio_storage.delete_object(object_key)
        result = await db.execute(select(StoredFile).where(StoredFile.storage_key == object_key))
        row = result.scalar_one_or_none()
        if row:
            await db.delete(row)
    except Exception:
        logger.warning("Failed to delete stored file %s", object_key, exc_info=True)


def media_kind_from_content_type(content_type: str) -> str:
    if content_type.startswith("image/"):
        return "image"
    if content_type.startswith("video/"):
        return "video"
    return "file"


# 兼容旧 import 名
presigned_get_url = build_file_download_url
