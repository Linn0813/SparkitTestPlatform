from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class VersionStatus(str, enum.Enum):
    planning = "planning"
    developing = "developing"
    releasing = "releasing"
    reviewing = "reviewing"
    ended = "ended"


class VersionNodeState(str, enum.Enum):
    pending = "pending"
    completed = "completed"


class VersionNodeProgress(Base):
    __tablename__ = "version_node_progress"
    __table_args__ = (UniqueConstraint("version_id", "node_key", name="uq_version_node"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("project_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state: Mapped[VersionNodeState] = mapped_column(
        String(16), nullable=False, default=VersionNodeState.pending.value
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    operator_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    assignee_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    scheduled_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    scheduled_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class VersionWecomNotifyRule(Base):
    __tablename__ = "version_wecom_notify_rules"
    __table_args__ = (UniqueConstraint("project_id", "event_key", name="uq_version_wecom_event"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    event_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message_template: Mapped[str] = mapped_column(Text, nullable=False)
    notify_user_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
