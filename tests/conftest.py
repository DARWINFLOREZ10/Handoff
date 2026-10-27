from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://flowforge:flowforge@127.0.0.1:5432/flowforge"
)
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("CELERY_BROKER_URL", "redis://127.0.0.1:6399/1")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6399/2")

import psycopg
import pytest
from fastapi.testclient import TestClient

from flowforge.app import create_app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def migrate() -> None:
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, check=True)


def _truncate() -> None:
    url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)
    with psycopg.connect(url, autocommit=True) as connection:
        connection.execute(
            "TRUNCATE TABLE audit_logs, jobs, workflow_executions, workflows, "
            "memberships, organizations, users RESTART IDENTITY CASCADE"
        )


@pytest.fixture()
def client():
    _truncate()
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def no_broker(monkeypatch: pytest.MonkeyPatch) -> None:
    from flowforge.workers import tasks

    monkeypatch.setattr(tasks.deliver_job_task, "delay", lambda job_id: job_id)
