from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.common import json_column
from app.models.user import _now, _uuid


class Inconsistency(Base):
    """Cross-document claim conflict (potential inconsistency - investigation recommended)."""

    __tablename__ = "inconsistencies"
    __table_args__ = (Index("ix_inconsistencies_company", "company_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(String(32), ForeignKey("companies.id"), nullable=False)
    topic: Mapped[str] = mapped_column(String(120), default="")
    claim_a: Mapped[str] = mapped_column(Text, default="")
    claim_b: Mapped[str] = mapped_column(Text, default="")
    source_a_document_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("documents.id"), nullable=True)
    source_a_page: Mapped[int] = mapped_column(Integer, default=0)
    source_b_document_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("documents.id"), nullable=True)
    source_b_page: Mapped[int] = mapped_column(Integer, default=0)
    explanation: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(12), default="medium")
    meta: Mapped[dict] = json_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ManagementQuestion(Base):
    __tablename__ = "management_questions"
    __table_args__ = (Index("ix_questions_company", "company_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(String(32), ForeignKey("companies.id"), nullable=False)
    topic: Mapped[str] = mapped_column(String(120), default="")
    question: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(12), default="medium", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"
    __table_args__ = (Index("ix_reports_company", "company_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(String(32), ForeignKey("companies.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="Executive Due Diligence Summary")
    status: Mapped[str] = mapped_column(String(20), default="complete", index=True)
    period_from: Mapped[str | None] = mapped_column(String(32), nullable=True)
    period_to: Mapped[str | None] = mapped_column(String(32), nullable=True)
    overall_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    content_json: dict = json_column()
    content_html: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class Citation(Base):
    """Maps evidence ids (SOURCE_N) used in answers/reports to real documents/pages."""

    __tablename__ = "citations"
    __table_args__ = (
        Index("ix_citations_message", "message_id"),
        Index("ix_citations_report", "report_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    report_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("analysis_reports.id"), nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("chat_messages.id"), nullable=True)
    evidence_id: Mapped[str] = mapped_column(String(24), default="")
    document_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("documents.id"), nullable=True)
    document_name: Mapped[str] = mapped_column(String(512), default="")
    page_number: Mapped[int] = mapped_column(Integer, default=0)
    section: Mapped[str] = mapped_column(String(255), default="")
    quote: Mapped[str] = mapped_column(Text, default="")
    relevance: Mapped[float] = mapped_column(Float, default=0.0)
