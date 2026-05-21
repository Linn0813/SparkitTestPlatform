from __future__ import annotations

import hashlib
import hmac
import logging
import time
import uuid
from typing import Optional
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)

_FILE_KEY_PREFIXES = ("bugs/", "projects/")


def _object_key(prefix: str, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    return f"{prefix}/{uuid.uuid4()}.{ext}"


def _sign_download_url(object_key: str, expires: int) -> str:
    payload = f"{object_key}\n{expires}"
    sig = hmac.new(
        settings.secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    base = settings.api_public_url.rstrip("/")
    q_key = quote(object_key, safe="")
    return f"{base}/api/v1/files/raw?object_key={q_key}&expires={expires}&signature={sig}"


def build_file_download_url(object_key: str, expires_seconds: int = 7 * 24 * 3600) -> str:
    expires = int(time.time()) + expires_seconds
    return _sign_download_url(object_key, expires)


def verify_download_signature(object_key: str, expires: int, signature: str) -> bool:
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
    row = StoredFile(
        storage_key=storage_key,
        filename=filename or "file.bin",
        content_type=content_type or "application/octet-stream",
        size=len(data),
        content=data,
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


async def delete_object_safe(db: AsyncSession, object_key: str) -> None:
    from app.models.stored_file import StoredFile

    if not object_key or not object_key.startswith(_FILE_KEY_PREFIXES):
        return
    try:
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
