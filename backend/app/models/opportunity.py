from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.user import _now, _uuid


class Opportunity(Base):
    __tablename__ = "opportunities"
    __table_args__ = (Index("ix_opportunities_company", "company_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(String(32), ForeignKey("companies.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    potential_impact: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[str] = mapped_column(String(12), default="medium")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class OpportunityEvidence(Base):
    __tablename__ = "opportunity_evidence"
    __table_args__ = (Index("ix_opportunity_evidence_opp", "opportunity_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    opportunity_id: Mapped[str] = mapped_column(String(32), ForeignKey("opportunities.id"), nullable=False)
    document_id: Mapped[str] = mapped_column(String(32), ForeignKey("documents.id"), nullable=False)
    document_name: Mapped[str] = mapped_column(String(512), default="")
    page_number: Mapped[int] = mapped_column(Integer, default=0)
    section: Mapped[str] = mapped_column(String(255), default="")
    quote: Mapped[str] = mapped_column(Text, default="")
