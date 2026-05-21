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
    access_token_expire_minutes: int = 1440
    cors_origins: str = "http://localhost:5174,http://127.0.0.1:5174"
    wecom_request_timeout: int = 5
    app_public_url: str = "http://localhost:5174"
    """文件下载签名链接的 API 根地址（给 img/video 用，需能访问后端）"""
    api_public_url: str = "http://127.0.0.1:8000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
