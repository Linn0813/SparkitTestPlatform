from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProjectRole(str, enum.Enum):
    project_admin = "project_admin"
    member = "member"
    tester = "tester"
    product = "product"
    developer = "developer"


class BusinessProjectRole(str, enum.Enum):
    """业务角色（不含 project_admin）。"""

    member = "member"
    tester = "tester"
    product = "product"
    developer = "developer"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    members: Mapped[list["ProjectMember"]] = relationship(back_populates="project")


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[BusinessProjectRole] = mapped_column(
        Enum(BusinessProjectRole), nullable=False, default=BusinessProjectRole.member
    )
    is_project_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    project: Mapped["Project"] = relationship(back_populates="members")
