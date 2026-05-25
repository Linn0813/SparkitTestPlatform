from typing import Any, Optional

from pydantic import BaseModel, Field


class TemplateFieldSchema(BaseModel):
    id: str
    name: str
    type: str
    required: bool = False
    options: list[str] = Field(default_factory=list)
    sort: int = 0


class FieldTemplateOut(BaseModel):
    project_id: str
    scene: str
    fields: list[dict[str, Any]]


class FieldTemplateUpdate(BaseModel):
    fields: list[dict[str, Any]]


class BugStatusOut(BaseModel):
    id: str
    project_id: str
    key: str
    label: str
    sort: int
    is_terminal: bool
    notify_wecom: bool
    notify_roles: list[str] = Field(default_factory=lambda: ["reporter", "followers"])

    model_config = {"from_attributes": True}


class BugStatusCreate(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)
    sort: int = 0
    is_terminal: bool = False
    notify_wecom: bool = False
    notify_roles: list[str] = Field(default_factory=lambda: ["reporter", "followers"])


class BugStatusUpdate(BaseModel):
    label: Optional[str] = None
    sort: Optional[int] = None
    is_terminal: Optional[bool] = None
    notify_wecom: Optional[bool] = None
    notify_roles: Optional[list[str]] = None


class WecomIntegrationOut(BaseModel):
    project_id: str
    wecom_webhook_url: Optional[str] = None
    wecom_enabled: bool
    app_public_url: Optional[str] = None
    status_notify_template: Optional[str] = None
    create_notify_template: Optional[str] = None
    notify_on_create: bool = True


class WecomIntegrationUpdate(BaseModel):
    wecom_webhook_url: Optional[str] = None
    wecom_enabled: Optional[bool] = None
    app_public_url: Optional[str] = None
    status_notify_template: Optional[str] = None
    create_notify_template: Optional[str] = None
    notify_on_create: Optional[bool] = None


class WecomTestRequest(BaseModel):
    message: str = "SparkitTestPlatform 企微连通性测试"


class RequirementRoleDefOut(BaseModel):
    id: str
    project_id: str
    role_key: str
    label: str
    sort: int

    model_config = {"from_attributes": True}


class RequirementRoleDefCreate(BaseModel):
    role_key: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)
    sort: int = 0


class RequirementRoleDefUpdate(BaseModel):
    role_key: Optional[str] = Field(default=None, min_length=1, max_length=64)
    label: Optional[str] = Field(default=None, min_length=1, max_length=128)
    sort: Optional[int] = None


class RequirementOptionDefOut(BaseModel):
    id: str
    project_id: str
    category: str
    option_key: str
    label: str
    sort: int

    model_config = {"from_attributes": True}


class RequirementOptionDefCreate(BaseModel):
    category: str = Field(min_length=1, max_length=32)
    option_key: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)
    sort: int = 0


class RequirementOptionDefUpdate(BaseModel):
    option_key: Optional[str] = Field(default=None, min_length=1, max_length=64)
    label: Optional[str] = Field(default=None, min_length=1, max_length=128)
    sort: Optional[int] = None
