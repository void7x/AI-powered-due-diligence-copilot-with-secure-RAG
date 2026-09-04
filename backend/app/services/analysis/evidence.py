"""Evidence resolution: connect detected risks/opportunities to real documents and
pages (the 'evidence graph' seam: company -> finding -> document evidence)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, FinancialMetric


def resolve_metric_evidence(db: Session, company_id: str, metric: str,
                            period_label: str) -> tuple[str | None, int, str]:
    """Returns (document_id, page, quote_snippet) for a metric, or (None, 0, '')."""
    row = db.execute(
        select(FinancialMetric)
        .where(FinancialMetric.company_id == company_id,
               FinancialMetric.metric == metric,
               FinancialMetric.period_label == period_label)
        .order_by(FinancialMetric.confidence.desc())
    ).scalars().first()
    if row is None or not row.source_document_id:
        return None, 0, ""
    doc = db.get(Document, row.source_document_id)
    quote = _find_quote(db, row.source_document_id, row.source_page, metric, row.value, period_label)
    return row.source_document_id, row.source_page, quote or (f"{metric} = {row.value:,.1f} ({period_label})")


def _find_quote(db: Session, document_id: str, page_number: int, metric: str,
                value: float, period_label: str) -> str:
    from app.models import DocumentPage
    page = db.execute(
        select(DocumentPage).where(DocumentPage.document_id == document_id,
                                   DocumentPage.page_number == page_number)
    ).scalars().first()
    if page is None:
        return ""
    import re
    label_word = metric.split("_")[0]
    pattern = re.compile(rf"[^\n]*{re.escape(label_word)}[^\n]*", re.IGNORECASE)
    match = pattern.search(page.extracted_text or "")
    if match:
        return match.group(0).strip()[:280]
    return f"{metric} = {value:,.1f} ({period_label})"


def chunk_quote_for_patterns(db: Session, company_id: str, patterns: list[str]) -> tuple[str | None, int, str] | None:
    """Find the first chunk matching any regex pattern -> (doc, page, quote)."""
    import re
    from app.models import DocumentChunk
    compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
    chunks = db.execute(
        select(DocumentChunk).where(DocumentChunk.company_id == company_id)
        .order_by(DocumentChunk.document_id, DocumentChunk.page_number)
    ).scalars().all()
    for chunk in chunks:
        for pattern in compiled:
            match = pattern.search(chunk.text)
            if match:
                start = max(0, match.start() - 60)
                quote = chunk.text[start : match.end() + 120].replace("\n", " ").strip()
                return chunk.document_id, chunk.page_number, f"...{quote}..."[:300]
    return None
