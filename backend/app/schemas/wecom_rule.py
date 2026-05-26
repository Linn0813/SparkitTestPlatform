from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase

WecomRuleKind = Literal["create", "transition", "comment"]
WecomEntityType = Literal["bug", "requirement"]


class WecomNotifyRuleOut(ORMBase):
    id: str
    project_id: str
    entity_type: WecomEntityType = "bug"
    kind: WecomRuleKind
    from_status_key: Optional[str] = None
    to_status_key: Optional[str] = None
    from_status_keys: list[str] = Field(default_factory=list)
    to_status_keys: list[str] = Field(default_factory=list)
    message_template: str
    notify_roles: list[str]
    enabled: bool
    created_at: datetime
    from_status_label: Optional[str] = None
    to_status_label: Optional[str] = None


class WecomNotifyRuleCreate(BaseModel):
    entity_type: WecomEntityType = "bug"
    kind: WecomRuleKind = "transition"
    from_status_key: Optional[str] = Field(default=None, max_length=64)
    to_status_key: Optional[str] = Field(default=None, max_length=64)
    from_status_keys: Optional[list[str]] = None
    to_status_keys: Optional[list[str]] = None
    message_template: str = Field(min_length=1)
    notify_roles: list[str] = Field(default_factory=lambda: ["reporter", "followers"])
    enabled: bool = True


class WecomNotifyRuleUpdate(BaseModel):
    from_status_key: Optional[str] = Field(default=None, max_length=64)
    to_status_key: Optional[str] = Field(default=None, max_length=64)
    from_status_keys: Optional[list[str]] = None
    to_status_keys: Optional[list[str]] = None
    message_template: Optional[str] = None
    notify_roles: Optional[list[str]] = None
    enabled: Optional[bool] = None


class WecomCreateRuleUpsert(BaseModel):
    message_template: Optional[str] = None
    notify_roles: Optional[list[str]] = None
    enabled: Optional[bool] = None


class WecomCommentRuleUpsert(BaseModel):
    entity_type: WecomEntityType
    message_template: Optional[str] = None
    notify_roles: Optional[list[str]] = None
    enabled: Optional[bool] = None
