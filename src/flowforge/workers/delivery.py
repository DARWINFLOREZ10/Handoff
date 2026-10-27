from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge.db.models import (
    AuditAction,
    AuditLog,
    ExecutionStatus,
    Job,
    JobStatus,
    WorkflowExecution,
)
from flowforge.db.session import async_session_factory


async def post_step(
    url: str,
    body: dict,
    idempotency_key: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> httpx.Response:
    async with httpx.AsyncClient(transport=transport) as client:
        return await client.post(
            url,
            json=body,
            headers={"Idempotency-Key": idempotency_key},
            timeout=10.0,
        )


async def deliver_job(job_id: UUID, transport: httpx.AsyncBaseTransport | None = None) -> None:
    async with async_session_factory() as session:
        await _deliver(session, job_id, transport)


async def _deliver(
    session: AsyncSession, job_id: UUID, transport: httpx.AsyncBaseTransport | None
) -> None:
    result = await session.execute(select(Job).where(Job.id == job_id).with_for_update())
    job = result.scalar_one_or_none()
    if job is None or job.status in (JobStatus.succeeded, JobStatus.failed):
        return

    job.attempts += 1
    job.status = JobStatus.running
    execution = await session.get(WorkflowExecution, job.workflow_execution_id)
    if execution is not None:
        execution.status = ExecutionStatus.running

    try:
        response = await post_step(
            str(job.payload["url"]),
            dict(job.payload.get("body") or {}),
            str(job.id),
            transport,
        )
        response.raise_for_status()
    except Exception as exc:
        exhausted = job.attempts >= job.max_retries
        message = str(exc)[:500]
        job.status = JobStatus.failed if exhausted else JobStatus.queued
        job.error_message = message
        action = AuditAction.job_failed if exhausted else AuditAction.job_retrying
        if execution is not None:
            execution.status = ExecutionStatus.failed if exhausted else ExecutionStatus.queued
            execution.error_message = message
            if exhausted:
                execution.finished_at = datetime.now(UTC)
        if execution is not None:
            session.add(
                AuditLog(
                    tenant_id=job.tenant_id,
                    actor_user_id=None,
                    action=action,
                    entity_type="workflow_execution",
                    entity_id=str(execution.id),
                    event_data={"job_id": str(job.id), "attempts": job.attempts},
                )
            )
        await session.commit()
        return

    job.status = JobStatus.succeeded
    job.error_message = None
    if execution is not None:
        execution.status = ExecutionStatus.succeeded
        execution.error_message = None
        execution.finished_at = datetime.now(UTC)
        session.add(
            AuditLog(
                tenant_id=job.tenant_id,
                actor_user_id=None,
                action=AuditAction.job_succeeded,
                entity_type="workflow_execution",
                entity_id=str(execution.id),
                event_data={"job_id": str(job.id), "attempts": job.attempts},
            )
        )
    await session.commit()
