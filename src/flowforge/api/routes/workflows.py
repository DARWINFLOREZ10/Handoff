from __future__ import annotations

import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge.api.deps import get_current_user, get_db_session, require_member
from flowforge.api.schemas import RunCreateRequest, RunRead, WorkflowCreateRequest, WorkflowRead
from flowforge.db.models import (
    AuditAction,
    AuditLog,
    ExecutionStatus,
    Job,
    JobStatus,
    Membership,
    User,
    Workflow,
    WorkflowExecution,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])
logger = logging.getLogger(__name__)


def enqueue_delivery(job_id: UUID) -> None:
    from flowforge.workers.tasks import deliver_job_task

    try:
        deliver_job_task.delay(str(job_id))
    except Exception:
        logger.exception("broker_unavailable job_id=%s", job_id)


def _workflow_read(workflow: Workflow) -> WorkflowRead:
    return WorkflowRead(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        target_url=str(workflow.definition["url"]),
    )


@router.post("", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreateRequest,
    membership: Membership = Depends(require_member),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> WorkflowRead:
    workflow = Workflow(
        tenant_id=membership.tenant_id,
        created_by_user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        definition={"url": str(payload.target_url)},
    )
    session.add(workflow)
    await session.flush()
    session.add(
        AuditLog(
            tenant_id=membership.tenant_id,
            actor_user_id=current_user.id,
            action=AuditAction.workflow_created,
            entity_type="workflow",
            entity_id=str(workflow.id),
            event_data={"url": str(payload.target_url)},
        )
    )
    await session.commit()
    return _workflow_read(workflow)


@router.post("/{workflow_id}/runs", response_model=RunRead, status_code=status.HTTP_201_CREATED)
async def start_run(
    workflow_id: UUID,
    payload: RunCreateRequest,
    membership: Membership = Depends(require_member),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> RunRead:
    workflow = await session.get(Workflow, workflow_id)
    if workflow is None or workflow.tenant_id != membership.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found.")

    execution_id = uuid4()
    job_id = uuid4()
    execution = WorkflowExecution(
        id=execution_id,
        tenant_id=membership.tenant_id,
        workflow_id=workflow.id,
        triggered_by_user_id=current_user.id,
        status=ExecutionStatus.queued,
        input_payload=payload.input_payload,
    )
    job = Job(
        id=job_id,
        tenant_id=membership.tenant_id,
        workflow_execution_id=execution_id,
        status=JobStatus.queued,
        payload={"url": workflow.definition["url"], "body": payload.input_payload},
        attempts=0,
        max_retries=3,
    )
    session.add(execution)
    await session.flush()
    session.add(job)
    session.add(
        AuditLog(
            tenant_id=membership.tenant_id,
            actor_user_id=current_user.id,
            action=AuditAction.run_queued,
            entity_type="workflow_execution",
            entity_id=str(execution_id),
            event_data={"job_id": str(job_id)},
        )
    )
    await session.commit()
    enqueue_delivery(job_id)
    return RunRead(
        id=execution_id,
        workflow_id=workflow.id,
        status=ExecutionStatus.queued,
        job_id=job_id,
        job_status=JobStatus.queued,
        attempts=0,
        audit=[AuditAction.run_queued.value],
    )


@router.get("/{workflow_id}/runs/{run_id}", response_model=RunRead)
async def get_run(
    workflow_id: UUID,
    run_id: UUID,
    membership: Membership = Depends(require_member),
    session: AsyncSession = Depends(get_db_session),
) -> RunRead:
    execution = await session.get(WorkflowExecution, run_id)
    if (
        execution is None
        or execution.workflow_id != workflow_id
        or execution.tenant_id != membership.tenant_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    job_result = await session.execute(select(Job).where(Job.workflow_execution_id == execution.id))
    job = job_result.scalar_one()
    audit_result = await session.execute(
        select(AuditLog.action)
        .where(AuditLog.entity_id == str(execution.id))
        .order_by(AuditLog.created_at.asc())
    )
    return RunRead(
        id=execution.id,
        workflow_id=execution.workflow_id,
        status=execution.status,
        job_id=job.id,
        job_status=job.status,
        attempts=job.attempts,
        audit=[action.value for action in audit_result.scalars().all()],
    )
