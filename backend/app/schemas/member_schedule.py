from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


ScheduleItemType = Literal["requirement_node_task", "bug"]


class MemberScheduleItemOut(BaseModel):
    item_type: ScheduleItemType = "requirement_node_task"
    id: str
    title: str
    assignee_id: str
    estimate_points: Optional[float] = None
    scheduled_start: Optional[date] = None
    scheduled_end: Optional[date] = None
    requirement_id: Optional[str] = None
    requirement_num: Optional[int] = None
    requirement_title: Optional[str] = None
    node_key: Optional[str] = None
    node_label: Optional[str] = None
    role_key: Optional[str] = None
    bug_id: Optional[str] = None
    bug_num: Optional[int] = None
    bug_title: Optional[str] = None


class MemberScheduleRowOut(BaseModel):
    user_id: str
    name: str
    scheduled_count: int = 0
    total_estimate_points: float = 0
    unscheduled_count: int = 0
    scheduled_items: list[MemberScheduleItemOut] = Field(default_factory=list)
    unscheduled_items: list[MemberScheduleItemOut] = Field(default_factory=list)


class MemberScheduleOut(BaseModel):
    range_start: date
    range_end: date
    members: list[MemberScheduleRowOut] = Field(default_factory=list)
