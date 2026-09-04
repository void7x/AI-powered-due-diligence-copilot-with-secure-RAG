"""Document processing pipeline:

Upload -> Validate -> Store -> Extract pages/tables -> Detect metadata ->
Chunk -> Embed -> Store chunks -> Extract financials -> READY
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core import db as _db
from app.core.logging import get_logger
from app.models import Document, DocumentChunk, DocumentPage, FinancialPeriod, FinancialMetric
from app.models.enums import DocumentStatus
from app.services.chunking.chunker import DocumentChunker
from app.services.extraction.classifier import classify_document
from app.services.extraction.registry import extract_any
from app.services.finance.extractor import extract_financials, upsert_financials

log = get_logger("app.ingestion")

EXT_TO_TYPE_HINT = {"pdf": "pdf", "docx": "docx", "pptx": "pptx", "xlsx": "xlsx", "csv": "csv", "txt": "txt"}


def _set_status(db: Session, document: Document, status: DocumentStatus,
                error: str | None = None) -> None:
    document.status = status.value
    document.error_message = error or ""
    db.commit()
    log.info("document status", extra={"document_id": document.id,
                                       "processing_status": status.value})


def process_document_sync(document_id: str) -> None:
    """Runs the full pipeline for one document. Used directly by tests/seeds and
    as the unit of work submitted to the job manager."""
    db = _db.SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None:
            log.error("document not found", extra={"document_id": document_id})
            return
        settings = get_settings()
        try:
            _set_status(db, document, DocumentStatus.EXTRACTING)
            result = extract_any(EXT_TO_TYPE_HINT[document.filename.rsplit(".", 1)[-1].lower()],
                                 document.storage_path)
            db.query(DocumentPage).filter(DocumentPage.document_id == document.id).delete()
            for page in result.pages:
                db.add(DocumentPage(
                    document_id=document.id, page_number=page.page_number,
                    extracted_text=page.text,
                    meta={"parser": result.parser, "page_basis": result.page_basis,
                          "approximate": page.approximate_page,
                          "tables": [{"headers": t.headers, "rows": t.rows[:200]} for t in page.tables]},
                ))
            document.page_count = len(result.pages)
            db.commit()

            # metadata: auto-classify type and fiscal year when missing
            sample_text = "\n".join(p.text for p in result.pages[:3])
            if document.fiscal_year is None:
                guessed_type, _conf, guessed_year = classify_document(document.filename, sample_text)
                if guessed_year:
                    document.fiscal_year = guessed_year
            if document.document_type in ("", "other"):
                guessed_type, _conf, _year = classify_document(document.filename, sample_text)
                document.document_type = guessed_type
            db.commit()

            _set_status(db, document, DocumentStatus.CHUNKING)
            chunker = DocumentChunker(settings)
            drafts = chunker.chunk(result, document_name=document.filename)

            _set_status(db, document, DocumentStatus.EMBEDDING)
            from app.services.embeddings.service import get_embedding_service
            embedder = get_embedding_service(settings)
            embeddings = embedder.embed_documents([d.text for d in drafts])

            db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
            for draft, vector in zip(drafts, embeddings):
                db.add(DocumentChunk(
                    document_id=document.id, company_id=document.company_id,
                    page_number=draft.page_number, chunk_index=draft.chunk_index,
                    section=draft.section, text=draft.text, token_count=draft.token_count,
                    fiscal_year=document.fiscal_year, document_type=document.document_type,
                    embedding=vector, meta={"document_name": document.filename},
                ))
            db.commit()

            _set_status(db, document, DocumentStatus.ANALYZING)
            metrics = extract_financials(result)
            periods_touched, stored = upsert_financials(db, document.company_id, document, metrics)
            log.info("financial extraction", extra={
                "document_id": document.id, "company_id": document.company_id,
                "processing_status": f"stored {stored} metrics across {periods_touched} periods"})

            document.processed_at = datetime.now(timezone.utc)
            _set_status(db, document, DocumentStatus.READY)
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            document = db.get(Document, document_id)
            if document is not None:
                _set_status(db, document, DocumentStatus.FAILED, error=str(exc)[:800])
            log.error("processing failed", extra={"document_id": document_id, "error": str(exc)})
            raise
    finally:
        db.close()


def delete_document_data(db: Session, document_id: str) -> None:
    """Cascade-clean everything derived from a document."""
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
    db.query(DocumentPage).filter(DocumentPage.document_id == document_id).delete()
    db.query(FinancialMetric).filter(FinancialMetric.source_document_id == document_id).delete()
    db.commit()
