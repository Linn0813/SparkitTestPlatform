from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RequirementPriority(str, enum.Enum):
    p00 = "p00"
    p0 = "p0"
    p1 = "p1"


class RequirementType(str, enum.Enum):
    feature = "feature"
    tech_optimization = "tech_optimization"


class RequirementStatus(str, enum.Enum):
    draft = "draft"
    pending_review = "pending_review"
    designing = "designing"
    developing = "developing"
    testing = "testing"
    pending_release = "pending_release"
    released = "released"
    completed = "completed"
    rejected = "rejected"
    closed = "closed"


class RequirementNodeState(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    skipped = "skipped"


class Requirement(Base):
    __tablename__ = "requirements"
    __table_args__ = (UniqueConstraint("project_id", "num", name="uq_requirement_project_num"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    num: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    external_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    version_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("project_versions.id"), nullable=True, index=True
    )
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="p1", index=True)
    req_type: Mapped[str] = mapped_column(String(32), nullable=False, default="feature", index=True)
    custom_fields: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[RequirementStatus] = mapped_column(
        Enum(RequirementStatus),
        nullable=False,
        default=RequirementStatus.draft,
        index=True,
    )
    frontend_rd_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    backend_rd_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    pm_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    tech_owner_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    qa_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    designer_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    role_assignee_ids: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    selected_role_keys: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RequirementNodeProgress(Base):
    __tablename__ = "requirement_node_progress"
    __table_args__ = (
        UniqueConstraint("requirement_id", "node_key", name="uq_requirement_node"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    requirement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("requirements.id"), nullable=False, index=True
    )
    node_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state: Mapped[RequirementNodeState] = mapped_column(
        Enum(RequirementNodeState),
        nullable=False,
        default=RequirementNodeState.pending,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    operator_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RequirementNodeTask(Base):
    __tablename__ = "requirement_node_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    requirement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("requirements.id"), nullable=False, index=True
    )
    node_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    role_key: Mapped[str] = mapped_column(String(64), nullable=False)
    assignee_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    estimate_points: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    scheduled_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    scheduled_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RequirementActivity(Base):
    __tablename__ = "requirement_activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    requirement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("requirements.id"), nullable=False, index=True
    )
    actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(String(512), nullable=False)
    detail: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class RequirementComment(Base):
    __tablename__ = "requirement_comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    requirement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("requirements.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class CaseRequirementLink(Base):
    __tablename__ = "case_requirement_links"
    __table_args__ = (UniqueConstraint("case_id", "requirement_id", name="uq_case_requirement"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("test_cases.id"), nullable=False, index=True)
    requirement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("requirements.id"), nullable=False, index=True
    )


class BugRequirementLink(Base):
    __tablename__ = "bug_requirement_links"
    __table_args__ = (UniqueConstraint("bug_id", "requirement_id", name="uq_bug_requirement"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    bug_id: Mapped[str] = mapped_column(String(36), ForeignKey("bugs.id"), nullable=False, index=True)
    requirement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("requirements.id"), nullable=False, index=True
    )


class BugPlanLink(Base):
    __tablename__ = "bug_plan_links"
    __table_args__ = (UniqueConstraint("bug_id", "plan_id", name="uq_bug_plan"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    bug_id: Mapped[str] = mapped_column(String(36), ForeignKey("bugs.id"), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("test_plans.id"), nullable=False, index=True)
