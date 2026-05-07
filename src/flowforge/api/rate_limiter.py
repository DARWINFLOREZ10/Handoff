from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address


def rate_limit_key(request: Request) -> str:
    tenant_id = request.headers.get("X-Tenant-ID", "anonymous")
    plan = request.headers.get("X-Tenant-Plan", "free")
    address = get_remote_address(request) or "unknown"
    return f"{tenant_id}:{plan}:{address}"


limiter = Limiter(key_func=rate_limit_key, default_limits=[])


async def rate_limit_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded."})
