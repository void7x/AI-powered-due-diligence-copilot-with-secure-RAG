from __future__ import annotations

import pathlib

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_scoped_company, get_scoped_document
from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import BadRequestError, NotFoundError
from app.core.jobs import get_job_manager
from app.core.logging import get_logger
from app.models import Document, DocumentPage, User
from app.models.enums import DocumentStatus, DocumentType
from app.schemas.document import DocumentOut, DocumentPageOut, DocumentStatusOut, DocumentUpdate
from app.services.ingestion.pipeline import delete_document_data, process_document_sync
from app.services.ingestion.storage import delete_stored_file, store_upload
from app.services.ingestion.validation import validate_magic_bytes, validate_upload
from app.utils.hashing import sha256_bytes

log = get_logger("app.documents")
router = APIRouter(tags=["documents"])

PROCESS_STEPS = ["EXTRACTING", "CHUNKING", "EMBEDDING", "ANALYZING"]


def _serialize(doc: Document) -> DocumentOut:
    return DocumentOut.model_validate(doc)


@router.post("/companies/{company_id}/documents", response_model=list[DocumentOut], status_code=201)
async def upload_documents(company_id: str,
                           files: list[UploadFile] = File(...),
                           document_type: str | None = Query(default=None),
                           fiscal_year: int | None = Query(default=None, ge=1990, le=2100),
                           db: Session = Depends(get_db),
                           company=Depends(get_scoped_company),
                           user: User = Depends(get_current_user)):
    settings = get_settings()
    created: list[Document] = []
    for upload in files:
        data = await upload.read()
        safe_name, ext = validate_upload(upload.filename or "upload", upload.content_type,
                                         len(data), settings)
        validate_magic_bytes(ext, data[:8])
        file_hash = sha256_bytes(data)
        duplicate = (db.query(Document)
                     .filter(Document.company_id == company.id, Document.file_hash == file_hash)
                     .first())
        if duplicate:
            raise BadRequestError(
                f"'{safe_name}' is a duplicate of an already-uploaded document "
                f"('{duplicate.filename}').", code="duplicate_document", status_code=409)
        path = store_upload(settings, company.id, safe_name, data)
        doc_type = document_type or DocumentType.OTHER.value
        doc = Document(
            company_id=company.id, filename=safe_name, document_type=doc_type,
            fiscal_year=fiscal_year, source_url="", file_hash=file_hash,
            storage_path=str(path), mime_type=upload.content_type or "",
            file_size=len(data), status=DocumentStatus.UPLOADED.value,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        created.append(doc)
        job = get_job_manager().create("document_process", PROCESS_STEPS, owner_user_id=user.id)
        get_job_manager().start(job, lambda j, doc_id=doc.id: process_document_sync(doc_id))
        log.info("document uploaded", extra={"document_id": doc.id,
                                             "company_id": company.id, "user_id": user.id})
    return [_serialize(d) for d in created]


@router.get("/companies/{company_id}/documents", response_model=list[DocumentOut])
def list_documents(company_id: str, q: str | None = None,
                   document_type: str | None = None,
                   fiscal_year: int | None = None,
                   status: str | None = None,
                   sort: str = "created_desc",
                   db: Session = Depends(get_db),
                   company=Depends(get_scoped_company)):
    query = db.query(Document).filter(Document.company_id == company.id)
    if q:
        query = query.filter(Document.filename.ilike(f"%{q}%"))
    if document_type:
        query = query.filter(Document.document_type == document_type)
    if fiscal_year:
        query = query.filter(Document.fiscal_year == fiscal_year)
    if status:
        query = query.filter(Document.status == status)
    if sort == "created_asc":
        query = query.order_by(Document.created_at)
    elif sort == "name_asc":
        query = query.order_by(Document.filename)
    else:
        query = query.order_by(Document.created_at.desc())
    return [_serialize(d) for d in query.all()]


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(db: Session = Depends(get_db), doc: Document = Depends(get_scoped_document)):
    return _serialize(doc)


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(db: Session = Depends(get_db), doc: Document = Depends(get_scoped_document)):
    delete_document_data(db, doc.id)
    delete_stored_file(doc.storage_path)
    db.delete(doc)
    db.commit()


@router.post("/documents/{document_id}/process", response_model=DocumentStatusOut)
def reprocess_document(db: Session = Depends(get_db), doc: Document = Depends(get_scoped_document),
                       user: User = Depends(get_current_user)):
    if doc.status in (DocumentStatus.PROCESSING.value, DocumentStatus.EXTRACTING.value,
                      DocumentStatus.CHUNKING.value, DocumentStatus.EMBEDDING.value):
        raise BadRequestError("Document is already being processed.")
    doc.status = DocumentStatus.UPLOADED.value
    doc.error_message = ""
    db.commit()
    job = get_job_manager().create("document_process", PROCESS_STEPS, owner_user_id=user.id)
    get_job_manager().start(job, lambda j: process_document_sync(doc.id))
    return DocumentStatusOut(id=doc.id, status=doc.status, page_count=doc.page_count)


@router.get("/documents/{document_id}/status", response_model=DocumentStatusOut)
def document_status(doc: Document = Depends(get_scoped_document)):
    progress = 100 if doc.status == DocumentStatus.READY.value else 0
    return DocumentStatusOut(id=doc.id, status=doc.status, page_count=doc.page_count,
                             error_message=doc.error_message, progress=progress)


@router.get("/documents/{document_id}/pages", response_model=list[DocumentPageOut])
def document_pages(page: int | None = Query(default=None, ge=1),
                   db: Session = Depends(get_db), doc: Document = Depends(get_scoped_document)):
    query = (db.query(DocumentPage).filter(DocumentPage.document_id == doc.id)
             .order_by(DocumentPage.page_number))
    if page:
        query = query.filter(DocumentPage.page_number == page)
    pages = query.all()
    return [DocumentPageOut(document_id=doc.id, page_number=p.page_number,
                            text=p.extracted_text, meta=p.meta or {}) for p in pages]


@router.get("/documents/{document_id}/file")
def document_file(doc: Document = Depends(get_scoped_document)):
    """Serve the original file using header-based authentication."""

    path = pathlib.Path(doc.storage_path)
    if not path.exists():
        raise NotFoundError("Stored file is missing.")
    return FileResponse(path, media_type=doc.mime_type or "application/octet-stream",
                        filename=doc.filename)
