from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import event

from flowforge.api.routes.workflows import enqueue_delivery
from flowforge.db.session import engine

commits: list[int] = []
event.listen(engine.sync_engine, "commit", lambda _connection: commits.append(1))


def register(client, email: str = "ada@example.com", name: str = "Ada") -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": name},
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    orgs = client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {token}"})
    assert orgs.status_code == 200
    return token, orgs.json()[0]["id"]


def headers(token: str, tenant: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant}


def test_register_login_and_refresh(client) -> None:
    token, _tenant = register(client)
    duplicate = client.post(
        "/api/v1/auth/register",
        json={"email": "ada@example.com", "password": "password123"},
    )
    assert duplicate.status_code == 409
    bad = client.post(
        "/api/v1/auth/login",
        json={"email": "ada@example.com", "password": "wrong-pass"},
    )
    assert bad.status_code == 401
    logged_in = client.post(
        "/api/v1/auth/login",
        json={"email": "ada@example.com", "password": "password123"},
    )
    assert logged_in.status_code == 200
    refresh = client.post(
        "/api/v1/auth/refresh-token",
        json={"refresh_token": logged_in.json()["refresh_token"]},
    )
    assert refresh.status_code == 200
    rejected = client.post(
        "/api/v1/auth/refresh-token",
        json={"refresh_token": token},
    )
    assert rejected.status_code == 401
    garbage = client.post("/api/v1/auth/refresh-token", json={"refresh_token": "not-a-jwt"})
    assert garbage.status_code == 401


def test_non_member_is_forbidden_and_missing_org_is_404(client) -> None:
    _token_a, tenant_a = register(client, "a@example.com", "Ann")
    token_b, _tenant_b = register(client, "b@example.com", "Bea")
    body = {"name": "Notify", "target_url": "http://example.test/hook"}
    forbidden = client.post("/api/v1/workflows", headers=headers(token_b, tenant_a), json=body)
    assert forbidden.status_code == 403
    missing = client.post("/api/v1/workflows", headers=headers(token_b, str(uuid4())), json=body)
    assert missing.status_code == 404
    assert (
        client.post(
            "/api/v1/workflows", headers={"Authorization": f"Bearer {token_b}"}, json=body
        ).status_code
        == 400
    )


def test_run_and_job_share_one_commit(client, monkeypatch) -> None:
    token, tenant = register(client)
    created = client.post(
        "/api/v1/workflows",
        headers=headers(token, tenant),
        json={
            "name": "Notify",
            "description": "One step",
            "target_url": "http://example.test/hook",
        },
    )
    assert created.status_code == 201, created.text
    workflow_id = created.json()["id"]
    assert created.json()["target_url"] == "http://example.test/hook"

    seen: dict[str, object] = {}

    def delay(job_id: str) -> None:
        seen["commits"] = len(commits)
        seen["job_id"] = job_id

    monkeypatch.setattr("flowforge.workers.tasks.deliver_job_task.delay", delay)
    commits.clear()
    started = client.post(
        f"/api/v1/workflows/{workflow_id}/runs",
        headers=headers(token, tenant),
        json={"input_payload": {"n": 1}},
    )
    assert started.status_code == 201, started.text
    body = started.json()
    assert seen["commits"] == 1
    assert seen["job_id"] == body["job_id"]
    assert body["status"] == "queued"
    assert body["attempts"] == 0
    assert "run_queued" in body["audit"]

    other = register(client, "other@example.com")
    hidden = client.post(
        f"/api/v1/workflows/{workflow_id}/runs",
        headers=headers(other[0], other[1]),
        json={"input_payload": {}},
    )
    assert hidden.status_code == 404
    unknown = client.post(
        f"/api/v1/workflows/{uuid4()}/runs",
        headers=headers(token, tenant),
        json={"input_payload": {}},
    )
    assert unknown.status_code == 404


def test_duplicate_slug_and_bad_url(client) -> None:
    token, _tenant = register(client)
    first = client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Lab", "slug": "lab-team"},
    )
    assert first.status_code == 201
    second = client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Lab", "slug": "lab-team"},
    )
    assert second.status_code == 409
    token_owner, tenant = register(client, "owner@example.com")
    invalid = client.post(
        "/api/v1/workflows",
        headers=headers(token_owner, tenant),
        json={"name": "Notify", "target_url": "not a url"},
    )
    assert invalid.status_code == 422


def test_enqueue_swallows_broker_errors(monkeypatch) -> None:
    def boom(_job_id: str) -> None:
        raise ConnectionError("broker down")

    monkeypatch.setattr("flowforge.workers.tasks.deliver_job_task.delay", boom)
    enqueue_delivery(UUID("123e4567-e89b-12d3-a456-426614174000"))
