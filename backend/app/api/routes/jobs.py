from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.core.jobs import get_job_manager
from app.models import User
from app.schemas.report import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, user: User = Depends(get_current_user)):
    job = get_job_manager().get(job_id)
    if job is None:
        raise NotFoundError("Job not found.")
    return JobOut(**job.as_dict())
