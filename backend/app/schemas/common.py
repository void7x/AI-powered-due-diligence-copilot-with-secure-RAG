from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EvidenceRef(ORMModel):
    """A pointer to a source location used across risks/opportunities/reports."""

    document_id: str
    document_name: str = ""
    page_number: int = 0
    section: str = ""
    quote: str = ""


class ErrorOut(BaseModel):
    error: dict
