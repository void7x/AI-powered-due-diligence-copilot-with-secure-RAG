from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class CitationOut(BaseModel):
    source_id: str
    document_id: str
    document_name: str
    page_number: int
    section: str = ""
    quote: str = ""
    relevance: float = 0.0


class ClaimOut(BaseModel):
    text: str
    type: str = "fact"          # fact | analysis | recommendation | uncertainty | contradiction
    sources: list[str] = []


class ChatAnswerOut(BaseModel):
    answer: str
    confidence: str = "medium"
    claims: list[ClaimOut] = []
    citations: list[CitationOut] = []
    insufficient_evidence: bool = False
    session_id: str = ""
    message_id: str = ""
    provider: str = "offline"


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    session_id: str | None = None
    document_types: list[str] | None = None
    fiscal_years: list[int] | None = None


class ChatMessageOut(ORMModel):
    id: str
    role: str
    content: str
    meta: dict
    created_at: datetime


class ChatSessionOut(ORMModel):
    id: str
    title: str
    created_at: datetime
    messages: list[ChatMessageOut] = []
