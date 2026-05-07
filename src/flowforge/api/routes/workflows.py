from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge.api.deps import get_current_user, get_tenant_or_404, get_db_session
from flowforge.api.schemas import (
    ExecutionRead,
    MessageResponse,
    WorkflowCancelRequest,
    WorkflowCreateRequest,
    WorkflowExecuteRequest,
    WorkflowRead,
    WorkflowRetryRequest,
    WorkflowUpdateRequest,
)
from flowforge.db.models import ExecutionStatus, Workflow, WorkflowExecution, WorkflowStatus, User, Organization

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=WorkflowRead)
async def create_workflow(
    payload: WorkflowCreateRequest,
    tenant: Organization = Depends(get_tenant_or_404),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> WorkflowRead:
    workflow = Workflow(
        tenant_id=tenant.id,
        created_by_user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        trigger_type=payload.trigger_type,
        definition=payload.definition,
        status=WorkflowStatus.draft,
    )
    session.add(workflow)
    await session.commit()
    return WorkflowRead(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        status=workflow.status,
        trigger_type=workflow.trigger_type,
        version=workflow.version,
    )


@router.patch("/{workflow_id}", response_model=WorkflowRead)
async def update_workflow(
    workflow_id: UUID,
    payload: WorkflowUpdateRequest,
) -> WorkflowRead:
    return WorkflowRead(
        id=workflow_id,
        name=payload.name or "workflow",
        description=payload.description,
        status=payload.status or WorkflowStatus.draft,
        trigger_type=payload.trigger_type or "manual",
        version=1,
    )


@router.post("/{workflow_id}/execute", response_model=ExecutionRead)
async def execute_workflow(
    workflow_id: UUID,
    payload: WorkflowExecuteRequest,
    tenant: Organization = Depends(get_tenant_or_404),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ExecutionRead:
    execution = WorkflowExecution(
        tenant_id=tenant.id,
        workflow_id=workflow_id,
        triggered_by_user_id=current_user.id,
        status=ExecutionStatus.queued,
        input_payload=payload.input_payload,
        correlation_id=payload.correlation_id,
    )
    session.add(execution)
    await session.commit()
    return ExecutionRead(
        id=execution.id,
        workflow_id=execution.workflow_id,
        status=execution.status,
        correlation_id=execution.correlation_id,
        duration_ms=execution.duration_ms,
    )


@router.post("/retry", response_model=MessageResponse)
async def retry_execution(payload: WorkflowRetryRequest) -> MessageResponse:
    return MessageResponse(detail=f"Execution {payload.execution_id} scheduled for retry.")


@router.post("/cancel", response_model=MessageResponse)
async def cancel_execution(payload: WorkflowCancelRequest) -> MessageResponse:
    return MessageResponse(detail=f"Execution {payload.execution_id} cancelled.")


@router.get("/{workflow_id}/history", response_model=list[ExecutionRead])
async def execution_history(workflow_id: UUID) -> list[ExecutionRead]:
    return [ExecutionRead(id=workflow_id, workflow_id=workflow_id, status=ExecutionStatus.queued, correlation_id=None, duration_ms=None)]
