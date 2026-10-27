from __future__ import annotations

from flowforge.main import app as flowforge_app
from flowforge.workers.celery_app import celery_app


def test_entrypoints_are_loaded() -> None:
    assert flowforge_app.title == "FlowForge"
    assert celery_app.main == "flowforge"
    assert "flowforge.deliver_job" in celery_app.tasks
