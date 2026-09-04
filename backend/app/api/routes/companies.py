from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_scoped_company
from app.core.db import get_db
from app.models import (
    AnalysisReport, Company, Document, Opportunity, Risk, User,
)
from app.models.enums import DocumentStatus
from app.schemas.company import (
    CompanyCreate, CompanyOut, CompanyOverviewOut, CompanySummaryOut, CompanyUpdate, ScoreCardOut,
)
from app.services.finance.service import financial_health_score, growth_potential_score, load_snapshot
from app.services.risk.engine import risk_level_label, run_risk_engine, risks_from_rows
from app.core.config import get_settings


def company_risk_state(db: Session, company: Company):
    """Prefer persisted analysis risks (includes qualitative ones); fall back to
    running the deterministic engine over current financials."""
    rows = (db.query(Risk).filter(Risk.company_id == company.id)
            .order_by(desc(Risk.score)).all())
    if rows:
        return risks_from_rows(rows), rows
    snapshot = load_snapshot(db, company.id)
    detected = run_risk_engine(snapshot, get_settings())
    return detected, []

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyOut, status_code=201)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)) -> Company:
    company = Company(user_id=user.id, **payload.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get("", response_model=list[CompanySummaryOut])
def list_companies(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    companies = db.query(Company).filter(Company.user_id == user.id).order_by(Company.created_at).all()
    out: list[CompanySummaryOut] = []
    for company in companies:
        out.append(_summary(db, company))
    return out


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company: Company = Depends(get_scoped_company)) -> Company:
    return company


@router.patch("/{company_id}", response_model=CompanyOut)
def update_company(payload: CompanyUpdate, db: Session = Depends(get_db),
                   company: Company = Depends(get_scoped_company)) -> Company:
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(company, key, value)
    company.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(company)
    return company


@router.delete("/{company_id}", status_code=204)
def delete_company(db: Session = Depends(get_db), company: Company = Depends(get_scoped_company)) -> None:
    from app.services.ingestion.storage import delete_stored_file
    for doc in db.query(Document).filter(Document.company_id == company.id).all():
        delete_stored_file(doc.storage_path)
    db.delete(company)
    db.commit()


@router.get("/{company_id}/overview", response_model=CompanyOverviewOut)
def company_overview(db: Session = Depends(get_db), company: Company = Depends(get_scoped_company)):
    settings = get_settings()
    snapshot = load_snapshot(db, company.id)
    detected, stored_rows = company_risk_state(db, company)
    from app.services.risk.engine import overall_risk_score
    overall = overall_risk_score(detected)
    health_score, health_level = financial_health_score(snapshot)
    growth_score, growth_level = growth_potential_score(snapshot)

    latest_report = (db.query(AnalysisReport).filter(AnalysisReport.company_id == company.id)
                     .order_by(desc(AnalysisReport.created_at)).first())
    docs = (db.query(Document).filter(Document.company_id == company.id)
            .order_by(desc(Document.created_at)).all())
    ready_count = sum(1 for d in docs if d.status == DocumentStatus.READY.value)
    risks_db = stored_rows[:5] if stored_rows else []
    opps_db = (db.query(Opportunity).filter(Opportunity.company_id == company.id)
               .order_by(desc(Opportunity.created_at)).limit(4).all())

    scorecards = [
        ScoreCardOut(label="Overall Risk", score=int(overall),
                     level=risk_level_label(overall),
                     detail=f"{len(detected)} risk signal(s) detected"),
        ScoreCardOut(label="Financial Health", score=health_score, level=health_level,
                     detail="Deterministic ratio blend"),
        ScoreCardOut(label="Growth Potential", score=growth_score, level=growth_level,
                     detail="Revenue CAGR + investment signals"),
        ScoreCardOut(label="Operational Risk",
                     score=_category_score(detected, {"cash_flow", "supplier_concentration", "execution"}),
                     level="", detail="Cash flow / suppliers / execution"),
        ScoreCardOut(label="Governance Risk",
                     score=_category_score(detected, {"governance", "management", "legal"}),
                     level="", detail="Governance / management / legal signals"),
    ]
    for card in scorecards:
        if not card.level:
            card.level = "low" if card.score < 35 else "medium" if card.score < 65 else "high"

    return CompanyOverviewOut(
        company=CompanyOut.model_validate(company),
        scorecards=scorecards,
        document_count=len(docs),
        ready_document_count=ready_count,
        last_analyzed_at=latest_report.created_at if latest_report else None,
        top_risks=[{"id": r.id, "title": r.title, "category": r.category,
                    "severity": r.severity, "score": r.score, "explanation": r.explanation}
                   for r in risks_db],
        top_opportunities=[{"id": o.id, "title": o.title, "category": o.category,
                            "confidence": o.confidence, "description": o.description}
                           for o in opps_db],
        recent_documents=[{"id": d.id, "filename": d.filename, "status": d.status,
                           "document_type": d.document_type, "fiscal_year": d.fiscal_year,
                           "created_at": d.created_at.isoformat()} for d in docs[:5]],
        revenue_trend=snapshot.trend_series(["total_revenue", "ebitda", "net_income"]),
        report_id=latest_report.id if latest_report else None,
    )


def _category_score(detected, categories: set[str]) -> int:
    relevant = [r for r in detected if r.category in categories]
    if not relevant:
        return 0
    weights = {"low": 25.0, "medium": 50.0, "high": 75.0, "critical": 95.0}
    return int(round(sum(weights[r.severity.value] for r in relevant) / len(relevant)))


def _summary(db: Session, company: Company) -> CompanySummaryOut:
    snapshot = load_snapshot(db, company.id)
    detected, _rows = company_risk_state(db, company)
    from app.services.risk.engine import overall_risk_score
    overall = overall_risk_score(detected)
    health, _ = financial_health_score(snapshot)
    growth, _ = growth_potential_score(snapshot)
    doc_count = db.execute(select(func.count()).select_from(Document)
                           .where(Document.company_id == company.id)).scalar() or 0
    last_report = (db.query(AnalysisReport).filter(AnalysisReport.company_id == company.id)
                   .order_by(desc(AnalysisReport.created_at)).first())
    base = CompanyOut.model_validate(company).model_dump()
    return CompanySummaryOut(
        **base,
        document_count=doc_count,
        risk_level=risk_level_label(overall),
        risk_score=overall,
        financial_health=health if snapshot.periods else None,
        growth_potential=growth if snapshot.periods else None,
        last_analyzed_at=last_report.created_at if last_report else None,
    )
