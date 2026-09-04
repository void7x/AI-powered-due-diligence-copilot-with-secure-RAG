from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_scoped_company
from app.core.db import get_db
from app.models import ChatMessage, ChatSession, Citation, User
from app.schemas.chat import ChatAnswerOut, ChatMessageOut, ChatRequest, ChatSessionOut
from app.services.rag.pipeline import RAGPipeline

router = APIRouter(prefix="/companies/{company_id}/chat", tags=["chat"])


@router.post("", response_model=ChatAnswerOut)
def chat(company_id: str, payload: ChatRequest, db: Session = Depends(get_db),
         company=Depends(get_scoped_company), user: User = Depends(get_current_user)) -> ChatAnswerOut:
    session = None
    if payload.session_id:
        session = (db.query(ChatSession)
                   .filter(ChatSession.id == payload.session_id,
                           ChatSession.company_id == company.id,
                           ChatSession.user_id == user.id).first())
    if session is None:
        session = ChatSession(company_id=company.id, user_id=user.id,
                              title=payload.question[:80])
        db.add(session)
        db.commit()
        db.refresh(session)

    db.add(ChatMessage(session_id=session.id, role="user", content=payload.question))
    db.commit()

    from app.core.config import get_settings
    pipeline = RAGPipeline(db, get_settings())
    result = pipeline.answer(
        company.id, payload.question,
        document_types=payload.document_types, fiscal_years=payload.fiscal_years,
    )

    assistant = ChatMessage(session_id=session.id, role="assistant", content=result.answer,
                            meta={"confidence": result.confidence,
                                  "insufficient_evidence": result.insufficient_evidence,
                                  "claims": result.claims, "provider": result.provider})
    db.add(assistant)
    db.commit()
    db.refresh(assistant)

    from app.schemas.chat import CitationOut, ClaimOut
    citations = []
    for c in result.citations:
        db.add(Citation(message_id=assistant.id, evidence_id=c["source_id"],
                        document_id=c["document_id"], document_name=c["document_name"],
                        page_number=c["page_number"], section=c["section"],
                        quote=c["quote"], relevance=c["relevance"]))
        citations.append(CitationOut(**c))
    db.commit()

    return ChatAnswerOut(
        answer=result.answer, confidence=result.confidence,
        claims=[ClaimOut(**cl) for cl in result.claims],
        citations=citations, insufficient_evidence=result.insufficient_evidence,
        session_id=session.id, message_id=assistant.id, provider=result.provider,
    )


@router.get("/sessions", response_model=list[ChatSessionOut])
def list_sessions(company_id: str, db: Session = Depends(get_db),
                  company=Depends(get_scoped_company), user: User = Depends(get_current_user)):
    sessions = (db.query(ChatSession)
                .filter(ChatSession.company_id == company.id, ChatSession.user_id == user.id)
                .order_by(ChatSession.created_at.desc()).limit(30).all())
    out = []
    for s in sessions:
        messages = (db.query(ChatMessage).filter(ChatMessage.session_id == s.id)
                    .order_by(ChatMessage.created_at).all())
        item = ChatSessionOut.model_validate(s)
        item.messages = [ChatMessageOut.model_validate(m) for m in messages]
        out.append(item)
    return out


@router.get("/messages", response_model=list[ChatMessageOut])
def latest_messages(company_id: str, db: Session = Depends(get_db),
                    company=Depends(get_scoped_company), user: User = Depends(get_current_user)):
    session = (db.query(ChatSession)
               .filter(ChatSession.company_id == company.id, ChatSession.user_id == user.id)
               .order_by(ChatSession.created_at.desc()).first())
    if session is None:
        return []
    messages = (db.query(ChatMessage).filter(ChatMessage.session_id == session.id)
                .order_by(ChatMessage.created_at).all())
    return [ChatMessageOut.model_validate(m) for m in messages]
