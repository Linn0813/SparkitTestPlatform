from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "mysql+aiomysql://sparkit:sparkit@127.0.0.1:3307/sparkit"
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

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
