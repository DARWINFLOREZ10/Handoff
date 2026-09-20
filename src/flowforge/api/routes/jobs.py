from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge.api.deps import get_current_user, get_db_session, get_tenant_or_404
from flowforge.api.schemas import JobQueueRequest, JobRead, JobRetryRequest, MessageResponse
from flowforge.db.models import AuditAction, AuditLog, Job, JobStatus, Organization, User

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobRead)
async def queue_job(
    payload: JobQueueRequest,
    tenant: Organization = Depends(get_tenant_or_404),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> JobRead:
    job = Job(
        tenant_id=tenant.id,
        job_type=payload.job_type,
        payload=payload.payload,
        queue_name=payload.queue_name,
        status=JobStatus.scheduled,
        run_at=payload.run_at,
    )
    session.add(job)
    await session.flush()
    session.add(
        AuditLog(
            tenant_id=tenant.id,
            actor_user_id=current_user.id,
            action=AuditAction.job_queued,
            entity_type="job",
            entity_id=str(job.id),
            event_data={"event": "job_queued", "job_type": payload.job_type},
        )
    )
    await session.commit()
    return JobRead(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        queue_name=job.queue_name,
        attempts=job.attempts,
    )


@router.post("/retry", response_model=MessageResponse)
async def retry_failed_job(payload: JobRetryRequest) -> MessageResponse:
    return MessageResponse(detail=f"Job {payload.job_id} queued for retry.")


@router.get("/scheduled", response_model=list[JobRead])
async def scheduled_jobs() -> list[JobRead]:
    return []


@router.get("/{job_id}/status", response_model=JobRead)
async def job_status(job_id: UUID) -> JobRead:
    return JobRead(
        id=job_id, job_type="generic", status=JobStatus.queued, queue_name="default", attempts=0
    )
