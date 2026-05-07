from __future__ import annotations

import asyncio
from types import SimpleNamespace

from starlette.requests import Request

from flowforge.api.rate_limiter import rate_limit_handler, rate_limit_key
from flowforge.main import app as flowforge_app
from flowforge.workers.beat import beat_schedule
from flowforge.workers.celery_app import celery_app
from flowforge.workers.tasks import (
    cleanup_scheduled_jobs_task,
    deliver_webhook_task,
    execute_api_call_task,
    generate_report_task,
    send_email_task,
)


class _FakeRequest:
    def __init__(self) -> None:
        self.headers = {"X-Tenant-ID": "tenant-123", "X-Tenant-Plan": "pro"}
        self.client = SimpleNamespace(host="127.0.0.1")


def _build_starlette_request() -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
            "scheme": "http",
            "root_path": "",
        }
    )


def test_entrypoints_are_loaded() -> None:
    assert flowforge_app.title == "FlowForge Platform"
    assert celery_app.main == "flowforge"
    assert "generate-daily-reports" in beat_schedule


def test_worker_tasks_return_payloads() -> None:
    assert send_email_task("a@example.com", "Subject", "Body")["status"] == "queued"
    assert deliver_webhook_task("https://example.com/webhook", {"ok": True})["status"] == "queued"
    assert execute_api_call_task("POST", "https://example.com/api", {"id": 1})["method"] == "POST"
    assert generate_report_task("tenant-1", "daily-executions")["status"] == "generated"
    assert cleanup_scheduled_jobs_task()["status"] == "completed"


def test_rate_limiter_helpers() -> None:
    fake_request = _FakeRequest()
    request = _build_starlette_request()

    assert rate_limit_key(fake_request) == "tenant-123:pro:127.0.0.1"
    response = asyncio.run(rate_limit_handler(request, Exception("limit")))
    assert response.status_code == 429
