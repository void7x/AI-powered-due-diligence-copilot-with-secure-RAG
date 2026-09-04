from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.common import embedding_column, json_column
from app.models.user import _uuid


class DocumentChunk(Base):
    """Retrievable unit with full source provenance (company/doc/page/section/fiscal year)."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_chunks_company", "company_id"),
        Index("ix_chunks_document", "document_id"),
        Index("ix_chunks_company_year", "company_id", "fiscal_year"),
        Index("ix_chunks_company_type", "company_id", "document_type"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(String(32), ForeignKey("documents.id"), nullable=False)
    company_id: Mapped[str] = mapped_column(String(32), ForeignKey("companies.id"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    section: Mapped[str] = mapped_column(String(255), default="")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    fiscal_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    document_type: Mapped[str] = mapped_column(String(40), default="other", index=True)
    embedding = embedding_column()
    meta: Mapped[dict] = json_column()
