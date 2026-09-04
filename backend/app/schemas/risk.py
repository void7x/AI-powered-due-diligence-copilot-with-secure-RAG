from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import EvidenceRef, ORMModel


class RiskEvidenceOut(EvidenceRef):
    id: str


class RiskOut(ORMModel):
    id: str
    company_id: str
    category: str
    title: str
    severity: str
    score: float
    explanation: str
    why_it_matters: str
    potential_impact: str
    recommendation: str
    confidence: str
    detected_signals: dict
    evidence: list[RiskEvidenceOut] = []
    created_at: datetime


class RiskSummaryOut(BaseModel):
    overall_score: float
    overall_level: str
    category_scores: dict = {}
    count_by_severity: dict = {}
