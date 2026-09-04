from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_scoped_company
from app.core.config import get_settings
from app.core.db import get_db
from app.core.jobs import get_job_manager
from app.models import (
    Company, Inconsistency, ManagementQuestion, Opportunity, OpportunityEvidence,
    Risk, RiskEvidence, User,
)
from app.models.enums import DocumentStatus
from app.schemas.opportunity import (
    InconsistencyOut, OpportunityEvidenceOut, OpportunityOut, QuestionOut,
)
from app.schemas.report import AnalyzeOut
from app.schemas.risk import RiskEvidenceOut, RiskOut
from app.services.analysis.orchestrator import STEPS, run_company_analysis
from app.services.finance.service import load_snapshot

router = APIRouter(prefix="/companies/{company_id}", tags=["analysis"])


@router.post("/analyze", response_model=AnalyzeOut)
def analyze(company_id: str, db: Session = Depends(get_db),
            company: Company = Depends(get_scoped_company),
            user: User = Depends(get_current_user)):
    from app.models import Document
    has_ready = (db.query(Document)
                 .filter(Document.company_id == company.id,
                         Document.status == DocumentStatus.READY.value).count()) > 0
    if not has_ready:
        from app.core.errors import InsufficientEvidenceError
        raise InsufficientEvidenceError(
            "No processed documents to analyze. Upload documents and wait for processing to finish.")
    manager = get_job_manager()
    job = manager.create("company_analysis", STEPS, owner_user_id=user.id)
    manager.start(job, lambda j: _run_in_own_session(company.id, j))
    return AnalyzeOut(job_id=job.id, status=job.status, steps=STEPS)


def _run_in_own_session(company_id: str, job) -> None:
    from app.core import db as _db
    from app.models import Company
    db = _db.SessionLocal()
    try:
        company = db.get(Company, company_id)
        if company is not None:
            run_company_analysis(db, company, job)
            job.result = {"company_id": company_id}
    finally:
        db.close()


@router.get("/risks", response_model=list[RiskOut])
def get_risks(company_id: str, db: Session = Depends(get_db),
              company: Company = Depends(get_scoped_company)):
    risks = (db.query(Risk).filter(Risk.company_id == company.id)
             .order_by(desc(Risk.score)).all())
    out = []
    for risk in risks:
        item = RiskOut.model_validate(risk)
        item.evidence = [RiskEvidenceOut.model_validate(e) for e in
                         db.query(RiskEvidence).filter(RiskEvidence.risk_id == risk.id).all()]
        out.append(item)
    return out


@router.get("/opportunities", response_model=list[OpportunityOut])
def get_opportunities(company_id: str, db: Session = Depends(get_db),
                      company: Company = Depends(get_scoped_company)):
    opportunities = (db.query(Opportunity).filter(Opportunity.company_id == company.id)
                     .order_by(desc(Opportunity.created_at)).all())
    out = []
    for opp in opportunities:
        item = OpportunityOut.model_validate(opp)
        item.evidence = [OpportunityEvidenceOut.model_validate(e) for e in
                         db.query(OpportunityEvidence)
                         .filter(OpportunityEvidence.opportunity_id == opp.id).all()]
        out.append(item)
    return out


@router.get("/inconsistencies", response_model=list[InconsistencyOut])
def get_inconsistencies(company_id: str, db: Session = Depends(get_db),
                        company: Company = Depends(get_scoped_company)):
    rows = (db.query(Inconsistency).filter(Inconsistency.company_id == company.id)
            .order_by(desc(Inconsistency.created_at)).all())
    return [InconsistencyOut.model_validate(r) for r in rows]


@router.get("/questions", response_model=list[QuestionOut])
def get_questions(company_id: str, db: Session = Depends(get_db),
                  company: Company = Depends(get_scoped_company)):
    rows = (db.query(ManagementQuestion).filter(ManagementQuestion.company_id == company.id)
            .order_by(ManagementQuestion.created_at).all())
    return [QuestionOut.model_validate(r) for r in rows]


@router.get("/financials")
def get_financials(company_id: str, db: Session = Depends(get_db),
                   company: Company = Depends(get_scoped_company)):
    snapshot = load_snapshot(db, company.id)
    from app.schemas.finance import FinancialsOut, MetricOut, PeriodOut, TrendPointOut
    periods_out = []
    for p in snapshot.periods:
        metrics = [
            MetricOut(metric=metric, value=value, period_label=p.period_label,
                      currency=snapshot.metric_sources.get(f"{p.period_label}:{metric}", {}).get("currency", "USD"),
                      unit=snapshot.metric_sources.get(f"{p.period_label}:{metric}", {}).get("unit", "million"),
                      source_document_id=snapshot.metric_sources.get(f"{p.period_label}:{metric}", {}).get("document_id"),
                      source_page=snapshot.metric_sources.get(f"{p.period_label}:{metric}", {}).get("page", 0),
                      confidence=snapshot.metric_sources.get(f"{p.period_label}:{metric}", {}).get("confidence", 0.5))
            for metric, value in p.values.items()
        ]
        periods_out.append(PeriodOut(period_label=p.period_label, fiscal_year=p.fiscal_year,
                                     currency="USD", unit="million",
                                     metrics=metrics,
                                     ratios=snapshot.ratios_by_period.get(p.period_label, {})))
    trends = [TrendPointOut(period_label=p.period_label,
                            values={
                                "revenue": p.values.get("total_revenue"),
                                "ebitda": p.values.get("ebitda"),
                                "net_income": p.values.get("net_income"),
                                "debt": p.values.get("total_debt"),
                                "cash": p.values.get("cash"),
                                "operating_cash_flow": p.values.get("operating_cash_flow"),
                                "free_cash_flow": p.values.get("free_cash_flow"),
                                "gross_margin": snapshot.ratio(p.period_label, "gross_margin"),
                                "operating_margin": snapshot.ratio(p.period_label, "operating_margin"),
                                "net_margin": snapshot.ratio(p.period_label, "net_margin"),
                            }) for p in snapshot.periods]
    return FinancialsOut(periods=periods_out, trends=trends, summary={
        "growth": snapshot.growth, "cagrs": snapshot.cagrs,
    }).model_dump()


@router.get("/financials/changes")
def get_changes(company_id: str, base: str, target: str,
                db: Session = Depends(get_db), company: Company = Depends(get_scoped_company)):
    from app.schemas.finance import ChangesOut
    from app.services.finance.trends import compute_changes
    snapshot = load_snapshot(db, company.id)
    return compute_changes(snapshot, base, target).model_dump()
