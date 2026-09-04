from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class OpportunityEvidenceOut(ORMModel):
    id: str
    document_id: str
    document_name: str = ""
    page_number: int = 0
    section: str = ""
    quote: str = ""


class OpportunityOut(ORMModel):
    id: str
    company_id: str
    category: str
    title: str
    description: str
    potential_impact: str
    confidence: str
    evidence: list[OpportunityEvidenceOut] = []
    created_at: datetime


class InconsistencyOut(ORMModel):
    id: str
    topic: str
    claim_a: str
    claim_b: str
    source_a_document_id: str | None
    source_a_page: int
    source_b_document_id: str | None
    source_b_page: int
    explanation: str
    severity: str
    created_at: datetime


class QuestionOut(ORMModel):
    id: str
    topic: str
    question: str
    rationale: str
    priority: str
