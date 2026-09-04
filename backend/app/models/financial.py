from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.user import _now, _uuid


class FinancialPeriod(Base):
    __tablename__ = "financial_periods"
    __table_args__ = (UniqueConstraint("company_id", "period_label", name="uq_period_company_label"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(String(32), ForeignKey("companies.id"), nullable=False)
    period_label: Mapped[str] = mapped_column(String(32), nullable=False)   # e.g. FY2025
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    unit: Mapped[str] = mapped_column(String(24), default="million")
    source_document_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("documents.id"), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class FinancialMetric(Base):
    """Normalized financial value with provenance. Kept separate from raw chunks."""

    __tablename__ = "financial_metrics"
    __table_args__ = (Index("ix_metrics_company_metric", "company_id", "metric"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(String(32), ForeignKey("companies.id"), nullable=False)
    period_id: Mapped[str] = mapped_column(String(32), ForeignKey("financial_periods.id"), nullable=False)
    period_label: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    unit: Mapped[str] = mapped_column(String(24), default="million")
    source_document_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("documents.id"), nullable=True)
    source_page: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
