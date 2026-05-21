from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RequirementStatus(str, enum.Enum):
    not_tested = "not_tested"
    testing = "testing"
    accepted = "accepted"


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
    status: Mapped[RequirementStatus] = mapped_column(
        Enum(RequirementStatus),
        nullable=False,
        default=RequirementStatus.not_tested,
        index=True,
    )
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


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
