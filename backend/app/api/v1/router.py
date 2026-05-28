from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    bugs,
    cases,
    dashboard,
    files,
    plans,
    projects,
    requirements,
    templates,
    users,
    version_wecom,
    versions,
    wecom_rules,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(projects.router)
api_router.include_router(templates.router)
api_router.include_router(cases.router)
api_router.include_router(requirements.router)
api_router.include_router(versions.router)
api_router.include_router(version_wecom.router)
api_router.include_router(plans.router)
api_router.include_router(bugs.router)
api_router.include_router(files.router)
api_router.include_router(dashboard.router)
api_router.include_router(wecom_rules.router)
