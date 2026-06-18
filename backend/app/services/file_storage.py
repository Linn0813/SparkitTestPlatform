from __future__ import annotations

import hashlib
import hmac
import logging
import mimetypes
import time
import uuid
from typing import Optional
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services import minio_storage

logger = logging.getLogger(__name__)

_FILE_KEY_PREFIXES = ("bugs/", "projects/", "ui-screenshots/", "ui-elements/", "ui-videos/")

# mimetypes 在部分环境对视频扩展名识别不完整
_EXTRA_MIME_BY_EXT: dict[str, str] = {
    ".mov": "video/quicktime",
    ".m4v": "video/x-m4v",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".ogg": "video/ogg",
}


def _object_key(prefix: str, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    return f"{prefix}/{uuid.uuid4()}.{ext}"


def _sanitize_filename_token(name: str) -> str:
    return name.replace("\\", "_").replace('"', "_")


def build_content_disposition(filename: str, disposition: str = "inline") -> str:
    """Build Content-Disposition header value safe for latin-1 HTTP headers (RFC 5987)."""
    if disposition == "inline":
        # 浏览器内联预览时不带 filename，避免中文名 latin-1 报错，也避免部分浏览器误触发下载。
        return "inline"

    safe_name = _sanitize_filename_token(filename)
    if filename.isascii():
        return f'attachment; filename="{safe_name}"'

    ascii_fallback = _sanitize_filename_token(filename.encode("ascii", "ignore").decode())
    if not ascii_fallback and "." in filename:
        ext = filename.rsplit(".", 1)[-1]
        if ext.isascii() and 0 < len(ext) <= 16:
            ascii_fallback = f"file.{ext}"
    if not ascii_fallback:
        ascii_fallback = "file"

    encoded = quote(filename, safe="")
    return f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded}'


def resolve_content_type(filename: str, stored_type: str | None) -> str:
    """Prefer stored MIME; fall back to extension guess instead of octet-stream."""
    stored = (stored_type or "").strip()
    if stored and stored != "application/octet-stream":
        return stored
    ext = f".{filename.rsplit('.', 1)[-1].lower()}" if "." in filename else ""
    if ext in _EXTRA_MIME_BY_EXT:
        return _EXTRA_MIME_BY_EXT[ext]
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or stored or "application/octet-stream"


def _sign_download(object_key: str, expires_seconds: int) -> tuple[int, str]:
    expires = int(time.time()) + expires_seconds
    signature = hmac.new(
        settings.secret_key.encode("utf-8"),
        f"{object_key}\n{expires}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return expires, signature


def build_file_download_url(object_key: str, expires_seconds: int = 7 * 24 * 3600) -> str:
    """经后端 /files/raw 代理的签名链接，浏览器无需直连 MinIO。"""
    expires, signature = _sign_download(object_key, expires_seconds)
    q = quote(object_key, safe="")
    path = f"/api/v1/files/raw?object_key={q}&expires={expires}&signature={signature}"
    base = settings.api_public_url.rstrip("/")
    if base.startswith("http://127.0.0.1") or base.startswith("http://localhost"):
        return path
    return f"{base}{path}"


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
