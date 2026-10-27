from __future__ import annotations

from celery import Celery

from flowforge.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "flowforge",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["flowforge.workers.tasks"],
)

celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
)
