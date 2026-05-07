from __future__ import annotations

from fastapi import APIRouter

from flowforge.api.routes import api_keys, audit_logs, auth, jobs, organizations, reports, workflows

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(workflows.router)
api_router.include_router(jobs.router)
api_router.include_router(reports.router)
api_router.include_router(audit_logs.router)
api_router.include_router(api_keys.router)
