"""Lightweight in-process background job manager.

MVP uses daemon threads; the interface (create/start/get + step updates) mirrors
a real queue API so swapping in Celery/RQ/Dramatiq is a drop-in change.
"""
from __future__ import annotations

import threading
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from app.core.logging import get_logger

log = get_logger("app.jobs")


@dataclass
class Job:
    id: str
    kind: str
    steps: list[str]
    status: str = "running"          # running | succeeded | failed
    current_step: str = ""
    progress: int = 0                # 0..100
    result: Any = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict:
        return {
            "id": self.id, "kind": self.kind, "status": self.status,
            "steps": self.steps, "current_step": self.current_step,
            "progress": self.progress, "result": self.result,
            "error": self.error, "created_at": self.created_at,
        }


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, kind: str, steps: list[str]) -> Job:
        job = Job(id=uuid.uuid4().hex[:16], kind=kind, steps=steps)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def start(self, job: Job, fn: Callable[..., Any], *args: Any) -> Job:
        def runner() -> None:
            try:
                fn(job, *args)
                job.status = "succeeded"
                job.progress = 100
            except Exception as exc:  # noqa: BLE001 - jobs must never crash the app
                job.status = "failed"
                job.error = str(exc) or exc.__class__.__name__
                log.error("job %s failed: %s", job.id, job.error,
                          extra={"job_id": job.id, "error": traceback.format_exc(limit=5)})
        threading.Thread(target=runner, daemon=True, name=f"job-{job.id}").start()
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def set_step(self, job: Job | None, step: str) -> None:
        if job is None:
            return
        job.current_step = step
        if step in job.steps:
            job.progress = int(((job.steps.index(step) + 1) / len(job.steps)) * 90)
        log.info("job step", extra={"job_id": job.id, "processing_status": step})


_manager = JobManager()


def get_job_manager() -> JobManager:
    return _manager
