from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MobilePlatform(str, enum.Enum):
    android = "android"
    ios = "ios"


class UITestCaseStatus(str, enum.Enum):
    draft = "draft"
    active = "active"


class UIRunStatus(str, enum.Enum):
    pending = "pending"      # 等待 Runner 领取
    running = "running"      # 执行中
    passed = "passed"        # 全部通过
    failed = "failed"        # 有步骤失败
    error = "error"          # 启动/连接异常


class UIStepStatus(str, enum.Enum):
    pending = "pending"
    passed = "passed"
    failed = "failed"
    skipped = "skipped"


# ---------------------------------------------------------------------------
# 元素库
# ---------------------------------------------------------------------------

class UIElement(Base):
    __tablename__ = "ui_elements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    platform: Mapped[MobilePlatform] = mapped_column(Enum(MobilePlatform), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    selector: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# UI 测试用例
# ---------------------------------------------------------------------------

class UITestCase(Base):
    __tablename__ = "ui_test_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[MobilePlatform] = mapped_column(Enum(MobilePlatform), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[UITestCaseStatus] = mapped_column(
        Enum(UITestCaseStatus), default=UITestCaseStatus.draft, nullable=False
    )

    # 每个元素的定位方式，格式：
    # {"email_input": "android=...", "submit_btn": "~Next", ...}
    selectors: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # 步骤列表，每步格式：
    # {"action": "tap"|"type"|"swipe"|"wait", "selector_key": "email_input", "value": "xxx"}
    steps: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # 成功条件，格式：
    # {"type": "element_visible", "selector_key": "home_ready"}
    assertion: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# App 包（APK / IPA）
# ---------------------------------------------------------------------------

class MobileApp(Base):
    __tablename__ = "mobile_apps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    platform: Mapped[MobilePlatform] = mapped_column(Enum(MobilePlatform), nullable=False)
    version: Mapped[str] = mapped_column(String(128), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)  # MinIO key
    size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


# ---------------------------------------------------------------------------
# Runner（执行机，即你的 Mac）
# ---------------------------------------------------------------------------

class UIRunner(Base):
    __tablename__ = "ui_runners"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # Runner 鉴权用
    platform: Mapped[MobilePlatform] = mapped_column(Enum(MobilePlatform), nullable=False)

    # Runner 最后一次心跳时间，超过 60s 视为离线
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


# ---------------------------------------------------------------------------
# 一次执行（点击"执行"后创建）
# ---------------------------------------------------------------------------

class UITestRun(Base):
    __tablename__ = "ui_test_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("ui_test_cases.id"), nullable=False, index=True)
    app_id: Mapped[str] = mapped_column(String(36), ForeignKey("mobile_apps.id"), nullable=False)
    runner_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("ui_runners.id"), nullable=True)

    status: Mapped[UIRunStatus] = mapped_column(
        Enum(UIRunStatus), default=UIRunStatus.pending, nullable=False, index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    triggered_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


# ---------------------------------------------------------------------------
# 每一步的执行结果
# ---------------------------------------------------------------------------

class UITestStepResult(Base):
    __tablename__ = "ui_test_step_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("ui_test_runs.id"), nullable=False, index=True)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 对应 steps 数组下标
    status: Mapped[UIStepStatus] = mapped_column(
        Enum(UIStepStatus), default=UIStepStatus.pending, nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    screenshot_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # MinIO key，失败时截图
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 该步耗时
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
