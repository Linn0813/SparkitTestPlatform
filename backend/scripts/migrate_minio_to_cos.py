"""
从云服务器 MinIO 迁移文件到腾讯云 COS。

用法：
  cd backend
  source .venv/bin/activate
  python3 scripts/migrate_minio_to_cos.py

说明：
  - 从云服务器 MinIO（43.131.62.217:9000）读取 sparkit bucket 所有文件
  - 上传到腾讯云 COS（从 .env.local 读取配置）
  - 已存在的文件自动跳过（幂等，可重跑）
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv('.env.local')

from minio import Minio
from io import BytesIO

# ── 云服务器旧 MinIO ──────────────────────────────────────
OLD_ENDPOINT = "127.0.0.1:9000"
OLD_ACCESS_KEY = "minioadmin"
OLD_SECRET_KEY = "minioadmin"
OLD_BUCKET = "sparkit"
OLD_SECURE = False

# ── 腾讯云 COS（从 .env.local 读） ────────────────────────
from app.core.config import settings


def main():
    old_client = Minio(
        OLD_ENDPOINT,
        access_key=OLD_ACCESS_KEY,
        secret_key=OLD_SECRET_KEY,
        secure=OLD_SECURE,
    )

    new_kwargs = {
        "access_key": settings.minio_access_key,
        "secret_key": settings.minio_secret_key,
        "secure": settings.minio_secure,
    }
    if settings.minio_region:
        new_kwargs["region"] = settings.minio_region
    new_client = Minio(settings.minio_endpoint, **new_kwargs)

    print(f"从 {OLD_ENDPOINT}/{OLD_BUCKET} 迁移到 {settings.minio_endpoint}/{settings.minio_bucket}")
    print("列举所有文件...")

    try:
        objects = list(old_client.list_objects(OLD_BUCKET, recursive=True))
    except Exception as e:
        print(f"无法连接旧 MinIO: {e}")
        print("请确认云服务器 MinIO 端口 9000 可访问（防火墙/安全组需放行）")
        sys.exit(1)

    total = len(objects)
    print(f"共 {total} 个文件\n")

    if total == 0:
        print("没有文件需要迁移")
        return

    success = 0
    skipped = 0
    failed = 0

    for i, obj in enumerate(objects, 1):
        key = obj.object_name
        size = obj.size or 0
        print(f"[{i}/{total}] {key} ({size:,} bytes)", end=" ... ", flush=True)

        try:
            # 检查 COS 是否已存在
            try:
                new_client.stat_object(settings.minio_bucket, key)
                print("已存在，跳过")
                skipped += 1
                continue
            except Exception:
                pass

            # 从旧 MinIO 读取
            response = old_client.get_object(OLD_BUCKET, key)
            try:
                data = response.read()
            finally:
                response.close()
                response.release_conn()

            # 上传到 COS
            content_type = obj.content_type or "application/octet-stream"
            new_client.put_object(
                settings.minio_bucket, key,
                BytesIO(data), length=len(data),
                content_type=content_type,
            )
            print("✓")
            success += 1

        except Exception as e:
            print(f"✗ {e}")
            failed += 1

    print(f"\n迁移完成：成功 {success}，跳过 {skipped}，失败 {failed}")
    if failed > 0:
        print("有文件失败，可重新运行脚本（已成功的会自动跳过）")


if __name__ == "__main__":
    main()
