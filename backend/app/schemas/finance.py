from __future__ import annotations

from pydantic import BaseModel


class MetricOut(BaseModel):
    metric: str
    value: float
    currency: str
    unit: str
    period_label: str
    source_document_id: str | None = None
    source_page: int = 0
    confidence: float = 0.5


class PeriodOut(BaseModel):
    period_label: str
    fiscal_year: int
    currency: str
    unit: str
    metrics: list[MetricOut] = []
    ratios: dict = {}


class TrendPointOut(BaseModel):
    period_label: str
    values: dict = {}


class FinancialsOut(BaseModel):
    periods: list[PeriodOut]
    trends: list[TrendPointOut] = []
    summary: dict = {}


class ChangeItemOut(BaseModel):
    label: str
    metric: str
    from_value: float | None
    to_value: float | None
    delta_pct: float | None = None
    delta_pts: float | None = None
    direction: str = "flat"       # up | down | flat
    sentiment: str = "neutral"    # positive | negative | neutral


class ChangesOut(BaseModel):
    from_period: str
    to_period: str
    items: list[ChangeItemOut]
    narrative: str = ""
