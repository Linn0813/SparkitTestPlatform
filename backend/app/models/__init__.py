from __future__ import annotations

from app.models.bug import (
    Bug,
    BugActivity,
    BugAttachment,
    BugCaseLink,
    BugComment,
    BugFollowerLink,
    BugStatusHistory,
)
from app.models.case import CaseModule, CasePriority, TestCase
from app.models.plan import ExecuteResult, PlanCase, PlanCaseResult, PlanStatus, TestPlan
from app.models.project import Project, ProjectMember, ProjectRole
from app.models.project_version import ProjectVersion
from app.models.requirement import BugPlanLink, BugRequirementLink, CaseRequirementLink, Requirement
from app.models.template import BugStatus, ProjectFieldTemplate, ProjectIntegration, TemplateScene
from app.models.wecom_rule import BugWecomNotifyRule
from app.models.stored_file import StoredFile
from app.models.user import User

__all__ = [
    "User",
    "Project",
    "ProjectMember",
    "ProjectRole",
    "TemplateScene",
    "ProjectFieldTemplate",
    "BugStatus",
    "ProjectIntegration",
    "CaseModule",
    "CasePriority",
    "TestCase",
    "PlanStatus",
    "ExecuteResult",
    "TestPlan",
    "PlanCase",
    "PlanCaseResult",
    "ProjectVersion",
    "Requirement",
    "CaseRequirementLink",
    "BugRequirementLink",
    "BugPlanLink",
    "Bug",
    "BugCaseLink",
    "BugFollowerLink",
    "BugAttachment",
    "BugStatusHistory",
    "BugComment",
    "BugActivity",
    "BugWecomNotifyRule",
    "StoredFile",
]
