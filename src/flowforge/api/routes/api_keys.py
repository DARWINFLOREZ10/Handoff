from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from flowforge.api.schemas import ApiKeyCreateRequest, ApiKeyResponse, MessageResponse

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post("", response_model=ApiKeyResponse)
async def create_api_key(payload: ApiKeyCreateRequest) -> ApiKeyResponse:
    return ApiKeyResponse(
        id=UUID(int=0),
        name=payload.name,
        key_prefix="ffk_live",
        scopes=payload.scopes,
        expires_at=payload.expires_at,
        revoked_at=None,
    )


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys() -> list[ApiKeyResponse]:
    return []


@router.post("/{key_id}/revoke", response_model=MessageResponse)
async def revoke_api_key(key_id: str) -> MessageResponse:
    return MessageResponse(detail=f"API key {key_id} revoked.")
