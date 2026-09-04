from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    ticker: str = Field(default="", max_length=32)
    industry: str = Field(default="", max_length=120)
    country: str = Field(default="", max_length=120)
    description: str = Field(default="", max_length=4000)


class CompanyUpdate(CompanyCreate):
    pass


class CompanyOut(ORMModel):
    id: str
    name: str
    ticker: str
    industry: str
    country: str
    description: str
    created_at: datetime
    updated_at: datetime


class ScoreCardOut(BaseModel):
    label: str
    score: int          # 0-100
    level: str          # low | medium | high | critical | strong ...
    detail: str = ""


class CompanyOverviewOut(BaseModel):
    company: CompanyOut
    scorecards: list[ScoreCardOut]
    document_count: int = 0
    ready_document_count: int = 0
    last_analyzed_at: datetime | None = None
    top_risks: list[dict] = []
    top_opportunities: list[dict] = []
    recent_documents: list[dict] = []
    revenue_trend: list[dict] = []
    report_id: str | None = None


class CompanySummaryOut(CompanyOut):
    document_count: int = 0
    risk_level: str = "unknown"
    risk_score: float = 0.0
    financial_health: int | None = None
    growth_potential: int | None = None
    last_analyzed_at: datetime | None = None
