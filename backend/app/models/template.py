from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TemplateScene(str, enum.Enum):
    functional_case = "functional_case"
    bug = "bug"


class ProjectFieldTemplate(Base):
    __tablename__ = "project_field_templates"
    __table_args__ = (UniqueConstraint("project_id", "scene", name="uq_project_scene"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    scene: Mapped[TemplateScene] = mapped_column(Enum(TemplateScene), nullable=False)
    fields: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class BugStatus(Base):
    __tablename__ = "bug_statuses"
    __table_args__ = (UniqueConstraint("project_id", "key", name="uq_project_status_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    sort: Mapped[int] = mapped_column(nullable=False, default=0)
    is_terminal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notify_wecom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notify_roles: Mapped[list] = mapped_column(
        JSON, nullable=False, default=lambda: ["reporter", "followers"]
    )


class ProjectIntegration(Base):
    __tablename__ = "project_integrations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, unique=True, index=True
    )
    wecom_webhook_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    wecom_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    app_public_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status_notify_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    create_notify_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notify_on_create: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
