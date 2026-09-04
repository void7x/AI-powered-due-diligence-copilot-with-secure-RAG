from __future__ import annotations

from pydantic import BaseModel


class SearchHit(BaseModel):
    document_id: str
    document_name: str
    document_type: str
    fiscal_year: int | None
    page_number: int
    section: str
    excerpt: str
    score: float


class SearchOut(BaseModel):
    query: str
    total: int
    hits: list[SearchHit]


class DashboardCompanyOut(BaseModel):
    id: str
    name: str
    ticker: str
    industry: str
    document_count: int = 0
    risk_level: str = "unknown"
    financial_health: int | None = None
    growth_potential: int | None = None
    last_analyzed_at: str | None = None


class ActivityItemOut(BaseModel):
    kind: str
    company_id: str
    company_name: str
    label: str
    at: str


class DashboardOut(BaseModel):
    companies: list[DashboardCompanyOut]
    totals: dict = {}
    recent_activity: list[ActivityItemOut] = []
