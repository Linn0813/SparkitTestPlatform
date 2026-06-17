from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PlanStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    archived = "archived"


class ExecuteResult(str, enum.Enum):
    not_run = "not_run"
    pass_ = "pass"
    fail = "fail"
    block = "block"
    skip = "skip"


class TestPlan(Base):
    __tablename__ = "test_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    version_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("project_versions.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[PlanStatus] = mapped_column(Enum(PlanStatus), default=PlanStatus.draft, nullable=False)
    owner_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PlanCase(Base):
    __tablename__ = "plan_cases"
    __table_args__ = (UniqueConstraint("plan_id", "case_id", name="uq_plan_case"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("test_plans.id"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("test_cases.id"), nullable=False, index=True)
    sort: Mapped[int] = mapped_column(nullable=False, default=0)


class PlanCaseResult(Base):
    __tablename__ = "plan_case_results"
    __table_args__ = (UniqueConstraint("plan_case_id", name="uq_plan_case_result"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_case_id: Mapped[str] = mapped_column(String(36), ForeignKey("plan_cases.id"), nullable=False, unique=True)
    executor_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    result: Mapped[ExecuteResult] = mapped_column(
        Enum(ExecuteResult), default=ExecuteResult.not_run, nullable=False
    )
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class PlanCaseResultComment(Base):
    __tablename__ = "plan_case_result_comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_case_id: Mapped[str] = mapped_column(String(36), ForeignKey("plan_cases.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
