from __future__ import annotations

from datetime import datetime, timezone

from flowforge.workers.celery_app import celery_app


@celery_app.task(name="flowforge.send_email")
def send_email_task(recipient: str, subject: str, body: str) -> dict[str, str]:
    return {
        "status": "queued",
        "recipient": recipient,
        "subject": subject,
        "body": body,
    }


@celery_app.task(name="flowforge.deliver_webhook")
def deliver_webhook_task(url: str, payload: dict) -> dict[str, object]:
    return {"status": "queued", "url": url, "payload": payload}


@celery_app.task(name="flowforge.execute_api_call")
def execute_api_call_task(method: str, url: str, payload: dict | None = None) -> dict[str, object]:
    return {"status": "queued", "method": method, "url": url, "payload": payload or {}}


@celery_app.task(name="flowforge.generate_report")
def generate_report_task(tenant_id: str, report_name: str) -> dict[str, str]:
    return {"status": "generated", "tenant_id": tenant_id, "report_name": report_name}


@celery_app.task(name="flowforge.cleanup_scheduled_jobs")
def cleanup_scheduled_jobs_task() -> dict[str, str]:
    return {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}
