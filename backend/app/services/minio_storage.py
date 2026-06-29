from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from functools import lru_cache
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache
def _client() -> Minio:
    kwargs = {
        "access_key": settings.minio_access_key,
        "secret_key": settings.minio_secret_key,
        "secure": settings.minio_secure,
    }
    if settings.minio_region:
        kwargs["region"] = settings.minio_region
    return Minio(settings.minio_endpoint, **kwargs)


def ensure_bucket_sync() -> None:
    client = _client()
    bucket = settings.minio_bucket
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
    except Exception:
        # 腾讯云 COS 等托管存储 bucket 已存在，bucket_exists 检查可能报错，直接跳过
        pass


async def ensure_bucket() -> None:
    await asyncio.to_thread(ensure_bucket_sync)


async def put_object(storage_key: str, data: bytes, content_type: str) -> None:
    def _put() -> None:
        ensure_bucket_sync()
        _client().put_object(
            settings.minio_bucket,
            storage_key,
            BytesIO(data),
            length=len(data),
            content_type=content_type or "application/octet-stream",
        )

    await asyncio.to_thread(_put)


async def get_object_bytes(storage_key: str) -> bytes | None:
    def _get() -> bytes | None:
        try:
            response = _client().get_object(settings.minio_bucket, storage_key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        except S3Error as exc:
            if exc.code in ("NoSuchKey", "NoSuchObject"):
                return None
            raise

    return await asyncio.to_thread(_get)


async def delete_object(storage_key: str) -> None:
    def _delete() -> None:
        try:
            _client().remove_object(settings.minio_bucket, storage_key)
        except S3Error as exc:
            if exc.code not in ("NoSuchKey", "NoSuchObject"):
                raise

    await asyncio.to_thread(_delete)


def presigned_get_url(storage_key: str, expires_seconds: int = 7 * 24 * 3600) -> str:
    ensure_bucket_sync()
    return _client().presigned_get_object(
        settings.minio_bucket,
        storage_key,
        expires=timedelta(seconds=expires_seconds),
    )
