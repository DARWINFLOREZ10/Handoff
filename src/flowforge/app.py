from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from flowforge.api.router import api_router
from flowforge.core.config import get_settings
from flowforge.core.logging import configure_logging


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""

    settings = get_settings()
    configure_logging(settings.log_level)

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    )

    origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix=settings.api_v1_prefix)

    @application.get("/health", tags=["system"])
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    return application
