from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_scoped_company
from app.core.config import get_settings
from app.core.db import get_db
from app.schemas.search import SearchHit, SearchOut
from app.services.retrieval.service import RetrievalService


class _NoopEmbedder:
    """Search endpoint is lexical; embedder never invoked (keyword_only=True)."""

    def embed_documents(self, texts):  # pragma: no cover
        raise NotImplementedError

    def embed_query(self, text):  # pragma: no cover
        raise NotImplementedError
from app.utils.text import excerpt_around

router = APIRouter(prefix="/companies/{company_id}/search", tags=["search"])


@router.get("", response_model=SearchOut)
def search(company_id: str, q: str = Query(min_length=2, max_length=300),
           document_type: str | None = None,
           fiscal_year: int | None = None,
           limit: int = Query(default=20, ge=1, le=50),
           db: Session = Depends(get_db), company=Depends(get_scoped_company)):
    service = RetrievalService(db, _NoopEmbedder(), get_settings())
    evidence = service.search(company.id, q,
                              document_types=[document_type] if document_type else None,
                              fiscal_years=[fiscal_year] if fiscal_year else None,
                              limit=limit)
    hits = [SearchHit(
        document_id=e.document_id, document_name=e.document_name,
        document_type=e.document_type, fiscal_year=e.fiscal_year,
        page_number=e.page_number, section=e.section,
        excerpt=excerpt_around(e.text.replace("\n", " "), next(iter(q.split()[:3]), q), 320),
        score=e.relevance,
    ) for e in evidence]
    return SearchOut(query=q, total=len(hits), hits=hits)
