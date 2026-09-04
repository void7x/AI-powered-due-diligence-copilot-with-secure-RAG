from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class DocumentOut(ORMModel):
    id: str
    company_id: str
    filename: str
    document_type: str
    fiscal_year: int | None
    source_url: str
    file_hash: str
    page_count: int
    status: str
    error_message: str
    file_size: int
    created_at: datetime
    processed_at: datetime | None


class DocumentStatusOut(BaseModel):
    id: str
    status: str
    page_count: int
    error_message: str = ""
    progress: int = 0


class DocumentPageOut(BaseModel):
    document_id: str
    page_number: int
    text: str
    meta: dict = {}


class DocumentUpdate(BaseModel):
    document_type: str | None = None
    fiscal_year: int | None = Field(default=None, ge=1990, le=2100)
    source_url: str | None = None
