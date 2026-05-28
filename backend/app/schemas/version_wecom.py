from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class VersionWecomIntegrationOut(BaseModel):
    project_id: str
    version_wecom_webhook_url: Optional[str] = None
    version_wecom_enabled: bool
    app_public_url: Optional[str] = None


class VersionWecomIntegrationUpdate(BaseModel):
    version_wecom_webhook_url: Optional[str] = None
    version_wecom_enabled: Optional[bool] = None
    app_public_url: Optional[str] = None


class VersionWecomTestRequest(BaseModel):
    message: str = "SparkitTestPlatform 版本企微连通性测试"


class VersionWecomNotifyRuleOut(ORMBase):
    id: str
    project_id: str
    node_key: str
    node_label: str
    message_template: str
    notify_user_ids: list[str] = Field(default_factory=list)
    enabled: bool


class VersionWecomNotifyRuleCreate(BaseModel):
    node_key: str
    message_template: str
    notify_user_ids: list[str] = Field(default_factory=list)
    enabled: bool = True


class VersionWecomNotifyRuleUpdate(BaseModel):
    message_template: Optional[str] = None
    notify_user_ids: Optional[list[str]] = None
    enabled: Optional[bool] = None


class VersionWecomNotifyRuleOptionOut(BaseModel):
    node_key: str
    node_label: str
    default_message_template: str
    configured: bool
