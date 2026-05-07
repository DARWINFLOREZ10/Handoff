from __future__ import annotations

from datetime import timedelta

beat_schedule = {
    "generate-daily-reports": {
        "task": "flowforge.generate_report",
        "schedule": timedelta(days=1),
        "args": ("system", "daily-executions"),
    },
    "cleanup-scheduled-jobs": {
        "task": "flowforge.cleanup_scheduled_jobs",
        "schedule": timedelta(hours=1),
    },
}
