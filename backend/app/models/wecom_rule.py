from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WecomNotifyRuleKind(str, enum.Enum):
    create = "create"
    transition = "transition"
    comment = "comment"


class WecomNotifyEntityType(str, enum.Enum):
    bug = "bug"
    requirement = "requirement"


class BugWecomNotifyRule(Base):
    __tablename__ = "bug_wecom_notify_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(16), nullable=False, default="bug", index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    from_status_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    to_status_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    from_status_keys: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    to_status_keys: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    message_template: Mapped[str] = mapped_column(Text, nullable=False)
    notify_roles: Mapped[list] = mapped_column(JSON, nullable=False, default=lambda: ["reporter", "followers"])
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
