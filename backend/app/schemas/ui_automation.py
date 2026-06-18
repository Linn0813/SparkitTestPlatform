from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.ui_automation import MobilePlatform, UIRunStatus, UIStepStatus, UITestCaseStatus
from app.schemas.common import ORMBase


# ---------------------------------------------------------------------------
# 元素库
# ---------------------------------------------------------------------------

class UIElementCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    platform: MobilePlatform
    selector: str = Field(min_length=1, max_length=512)
    description: Optional[str] = None


class UIElementUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    selector: Optional[str] = Field(default=None, min_length=1, max_length=512)
    description: Optional[str] = None


class UIElementOut(ORMBase):
    id: str
    project_id: str
    platform: MobilePlatform
    name: str
    selector: str
    description: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# UI 测试用例
# ---------------------------------------------------------------------------

class UITestCaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    platform: MobilePlatform
    description: Optional[str] = None
    selectors: dict[str, str] = Field(default_factory=dict)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    assertion: dict[str, Any] = Field(default_factory=dict)


class UITestCaseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[UITestCaseStatus] = None
    selectors: Optional[dict[str, str]] = None
    steps: Optional[list[dict[str, Any]]] = None
    assertion: Optional[dict[str, Any]] = None


class UITestCaseOut(ORMBase):
    id: str
    project_id: str
    name: str
    platform: MobilePlatform
    description: Optional[str]
    status: UITestCaseStatus
    selectors: dict[str, Any]
    steps: list[Any]
    assertion: dict[str, Any]
    created_by: str
    created_at: datetime
    updated_at: datetime


class UITestCaseListItem(ORMBase):
    id: str
    name: str
    platform: MobilePlatform
    status: UITestCaseStatus
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# App 包
# ---------------------------------------------------------------------------

class MobileAppOut(ORMBase):
    id: str
    project_id: str
    platform: MobilePlatform
    version: str
    filename: str
    size: int
    uploaded_by: str
    uploaded_at: datetime


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class UIRunnerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    platform: MobilePlatform


class UIRunnerOut(ORMBase):
    id: str
    project_id: str
    name: str
    platform: MobilePlatform
    last_heartbeat_at: Optional[datetime]
    created_at: datetime

    @property
    def is_online(self) -> bool:
        if not self.last_heartbeat_at:
            return False
        from datetime import timezone
        delta = datetime.now(timezone.utc).replace(tzinfo=None) - self.last_heartbeat_at
        return delta.total_seconds() < 60


class UIRunnerWithToken(UIRunnerOut):
    token: str


# ---------------------------------------------------------------------------
# 执行
# ---------------------------------------------------------------------------

class UITestRunCreate(BaseModel):
    case_id: str
    app_id: str


class UITestStepResultOut(ORMBase):
    id: str
    run_id: str
    step_index: int
    status: UIStepStatus
    error_message: Optional[str]
    screenshot_key: Optional[str]
    screenshot_url: Optional[str] = None
    duration_ms: Optional[int]
    executed_at: Optional[datetime]


class UITestRunOut(ORMBase):
    id: str
    project_id: str
    case_id: str
    app_id: str
    runner_id: Optional[str]
    status: UIRunStatus
    error_message: Optional[str]
    video_key: Optional[str] = None
    video_url: Optional[str] = None
    triggered_by: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime
    step_results: list[UITestStepResultOut] = Field(default_factory=list)


class UITestRunListItem(ORMBase):
    id: str
    case_id: str
    app_id: str
    runner_id: Optional[str]
    status: UIRunStatus
    triggered_by: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime
