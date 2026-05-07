from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter

from flowforge.api.schemas import AuditLogResponse
from flowforge.db.models import AuditAction

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=list[AuditLogResponse])
async def list_audit_logs() -> list[AuditLogResponse]:
    return [
        AuditLogResponse(
            id=UUID(int=0),
            action=AuditAction.login,
            entity_type="system",
            entity_id=None,
            metadata={},
            created_at=datetime.now(timezone.utc),
        )
    ]
