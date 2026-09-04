from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class ReportOut(ORMModel):
    id: str
    company_id: str
    title: str
    status: str
    period_from: str | None
    period_to: str | None
    overall_risk_score: float
    created_at: datetime


class ReportDetailOut(ReportOut):
    content: dict = {}


class AnalyzeOut(BaseModel):
    job_id: str
    status: str
    steps: list[str]


class JobOut(BaseModel):
    id: str
    kind: str
    status: str
    steps: list[str]
    current_step: str
    progress: int
    result: dict | list | str | int | float | None = None
    error: str | None = None
    created_at: str
