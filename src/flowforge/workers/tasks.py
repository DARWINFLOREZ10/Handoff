from __future__ import annotations

import asyncio
from uuid import UUID

from flowforge.workers.celery_app import celery_app
from flowforge.workers.delivery import deliver_job


@celery_app.task(name="flowforge.deliver_job")
def deliver_job_task(job_id: str) -> str:
    asyncio.run(deliver_job(UUID(job_id)))
    return job_id
