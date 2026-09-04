"""FastAPI dependencies: DB session, auth, tenant-scoped company access."""
from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import InvalidTokenError, decode_access_token
from app.models import Company, Document, User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth = request.headers.get("Authorization", "")
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    if not token:
        raise UnauthorizedError("Missing authentication token.")
    try:
        payload = decode_access_token(token, get_settings().secret_key)
    except InvalidTokenError as exc:
        raise UnauthorizedError(f"Invalid or expired token: {exc}") from exc
    user = db.get(User, payload.get("sub", ""))
    if user is None:
        raise UnauthorizedError("User no longer exists.")
    return user


def get_scoped_company(company_id: str, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)) -> Company:
    """Tenant isolation: companies are only accessible to their owner."""
    company = db.get(Company, company_id)
    if company is None:
        raise NotFoundError("Company not found.")
    if company.user_id != user.id:
        raise ForbiddenError("You do not have access to this company.")
    return company


def get_scoped_document(document_id: str, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)) -> Document:
    """Resolve a document and verify tenant ownership via its company."""
    doc = db.get(Document, document_id)
    if doc is None:
        raise NotFoundError("Document not found.")
    company = db.get(Company, doc.company_id)
    if company is None or company.user_id != user.id:
        raise NotFoundError("Document not found.")
    return doc
