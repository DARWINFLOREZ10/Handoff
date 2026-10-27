from __future__ import annotations

import asyncio
import json
from uuid import UUID, uuid4

import httpx

from flowforge.workers.delivery import deliver_job
from flowforge.workers.tasks import deliver_job_task


def _start(client) -> tuple[str, str, str]:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "worker@example.com", "password": "password123", "full_name": "Worker"},
    )
    token = registered.json()["access_token"]
    tenant = client.get(
        "/api/v1/organizations", headers={"Authorization": f"Bearer {token}"}
    ).json()[0]["id"]
    auth = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant}
    created = client.post(
        "/api/v1/workflows",
        headers=auth,
        json={"name": "Notify", "target_url": "http://example.test/hook"},
    )
    workflow_id = created.json()["id"]
    started = client.post(
        f"/api/v1/workflows/{workflow_id}/runs",
        headers=auth,
        json={"input_payload": {"hello": "world"}},
    )
    body = started.json()
    return workflow_id, body["id"], body["job_id"]


def _read(client, workflow_id: str, run_id: str) -> dict:
    registered = client.post(
        "/api/v1/auth/login",
        json={"email": "worker@example.com", "password": "password123"},
    )
    token = registered.json()["access_token"]
    tenant = client.get(
        "/api/v1/organizations", headers={"Authorization": f"Bearer {token}"}
    ).json()[0]["id"]
    response = client.get(
        f"/api/v1/workflows/{workflow_id}/runs/{run_id}",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_failure_retries_then_success_is_not_sent_twice(client) -> None:
    workflow_id, run_id, job_id = _start(client)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        assert request.headers["Idempotency-Key"] == job_id
        assert json.loads(request.content) == {"hello": "world"}
        if calls["n"] == 1:
            raise httpx.ConnectError("down")
        return httpx.Response(204)

    transport = httpx.MockTransport(handler)
    asyncio.run(deliver_job(UUID(job_id), transport))
    retried = _read(client, workflow_id, run_id)
    assert retried["job_status"] == "queued"
    assert retried["attempts"] == 1
    assert "job_retrying" in retried["audit"]

    asyncio.run(deliver_job(UUID(job_id), transport))
    done = _read(client, workflow_id, run_id)
    assert done["job_status"] == "succeeded"
    assert done["status"] == "succeeded"
    assert "job_succeeded" in done["audit"]

    asyncio.run(deliver_job(UUID(job_id), transport))
    assert calls["n"] == 2


def test_attempt_budget_marks_the_job_failed(client) -> None:
    workflow_id, run_id, job_id = _start(client)
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ConnectError("down")

    transport = httpx.MockTransport(handler)
    for _ in range(3):
        asyncio.run(deliver_job(UUID(job_id), transport))
    failed = _read(client, workflow_id, run_id)
    assert failed["job_status"] == "failed"
    assert failed["status"] == "failed"
    assert failed["attempts"] == 3
    assert "job_failed" in failed["audit"]
    asyncio.run(deliver_job(UUID(job_id), transport))
    assert calls["n"] == 3


def test_missing_job_is_a_no_op() -> None:
    asyncio.run(deliver_job(uuid4()))


def test_celery_task_delegates(monkeypatch) -> None:
    seen: dict[str, UUID] = {}

    async def fake(job_id: UUID, transport=None) -> None:
        seen["job_id"] = job_id

    monkeypatch.setattr("flowforge.workers.tasks.deliver_job", fake)
    job_id = uuid4()
    assert deliver_job_task(str(job_id)) == str(job_id)
    assert seen["job_id"] == job_id
