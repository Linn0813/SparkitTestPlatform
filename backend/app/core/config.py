from __future__ import annotations

import socket
from typing import Optional
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _can_connect(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _is_local_database_url(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return False
    return host in {"127.0.0.1", "localhost", "::1"}


def _resolve_deploy_host(lan: Optional[str], wan: Optional[str], port: int) -> Optional[str]:
    for host in (lan, wan):
        if host and _can_connect(host, port):
            return host
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.local", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "mysql+aiomysql://sparkit:sparkit@127.0.0.1:3307/sparkit"
    database_host_lan: Optional[str] = None
    database_host_wan: Optional[str] = None
    database_port: int = 3307
    # SQLAlchemy 连接池（单进程单 Engine，不会每请求新建连接）
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle: int = 1800
    db_pool_timeout: int = 30
    db_pool_pre_ping: bool = True
    db_connect_timeout: int = 10
    db_echo: bool = False
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 10080  # 7 days
    cors_origins: str = "http://localhost:5174,http://127.0.0.1:5174"
    wecom_request_timeout: int = 5
    app_public_url: str = "http://localhost:5174"
    """文件下载签名链接的 API 根地址；默认 localhost 时返回相对路径 /api/v1/files/raw（经前端代理）"""
    api_public_url: str = "http://127.0.0.1:8000"

    minio_endpoint: str = "127.0.0.1:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "sparkit"
    minio_secure: bool = False

    @model_validator(mode="after")
    def resolve_remote_deploy_hosts(self):
        """开发机连远程部署库：按 LAN → WAN 探测，优先内网。"""
        if _is_local_database_url(self.database_url):
            return self
        if not self.database_host_lan and not self.database_host_wan:
            return self
        host = _resolve_deploy_host(self.database_host_lan, self.database_host_wan, self.database_port)
        if not host:
            return self
        self.database_url = (
            f"mysql+aiomysql://sparkit:sparkit@{host}:{self.database_port}/sparkit"
        )
        self.minio_endpoint = f"{host}:9000"
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
