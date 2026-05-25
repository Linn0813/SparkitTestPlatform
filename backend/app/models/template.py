from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TemplateScene(str, enum.Enum):
    functional_case = "functional_case"
    bug = "bug"
    requirement = "requirement"


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


class RequirementRoleDef(Base):
    __tablename__ = "requirement_role_defs"
    __table_args__ = (UniqueConstraint("project_id", "role_key", name="uq_project_req_role_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    role_key: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class RequirementOptionDef(Base):
    __tablename__ = "requirement_option_defs"
    __table_args__ = (
        UniqueConstraint("project_id", "category", "option_key", name="uq_project_req_option_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    option_key: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class RequirementWorkflowNodeDef(Base):
    __tablename__ = "requirement_workflow_node_defs"
    __table_args__ = (
        UniqueConstraint("project_id", "node_key", name="uq_project_req_wf_node_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    node_key: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    role_keys: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    lane_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lane_indexes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    blocks_lane_gate: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_in_lane: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
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
