from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.common import json_column
from app.models.user import _now, _uuid


class Risk(Base):
    __tablename__ = "risks"
    __table_args__ = (Index("ix_risks_company", "company_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(String(32), ForeignKey("companies.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(12), default="medium", index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    explanation: Mapped[str] = mapped_column(Text, default="")       # what we found
    why_it_matters: Mapped[str] = mapped_column(Text, default="")
    potential_impact: Mapped[str] = mapped_column(Text, default="")
    recommendation: Mapped[str] = mapped_column(Text, default="")    # what to investigate next
    confidence: Mapped[str] = mapped_column(String(12), default="medium")
    detected_signals: Mapped[dict] = json_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class RiskEvidence(Base):
    __tablename__ = "risk_evidence"
    __table_args__ = (Index("ix_risk_evidence_risk", "risk_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    risk_id: Mapped[str] = mapped_column(String(32), ForeignKey("risks.id"), nullable=False)
    document_id: Mapped[str] = mapped_column(String(32), ForeignKey("documents.id"), nullable=False)
    document_name: Mapped[str] = mapped_column(String(512), default="")
    page_number: Mapped[int] = mapped_column(Integer, default=0)
    section: Mapped[str] = mapped_column(String(255), default="")
    quote: Mapped[str] = mapped_column(Text, default="")
