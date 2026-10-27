from __future__ import annotations

from fastapi import APIRouter

from flowforge.api.routes import auth, organizations, workflows

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(workflows.router)
