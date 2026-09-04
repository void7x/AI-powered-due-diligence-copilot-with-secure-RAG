from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import AnalysisReport, Company, Document, User
from app.schemas.search import ActivityItemOut, DashboardCompanyOut, DashboardOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.api.routes.companies import _summary
    companies = db.query(Company).filter(Company.user_id == user.id).all()
    cards = [_summary(db, c) for c in companies]
    company_cards = [DashboardCompanyOut(
        id=c.id, name=c.name, ticker=c.ticker, industry=c.industry,
        document_count=c.document_count, risk_level=c.risk_level,
        financial_health=c.financial_health, growth_potential=c.growth_potential,
        last_analyzed_at=c.last_analyzed_at.isoformat() if c.last_analyzed_at else None,
    ) for c in cards]

    activity: list[ActivityItemOut] = []
    company_map = {c.id: c.name for c in companies}
    docs = (db.execute(select(Document).where(Document.company_id.in_(list(company_map) or [""]))
                       .order_by(desc(Document.created_at)).limit(8)).scalars().all())
    for d in docs:
        activity.append(ActivityItemOut(
            kind="document", company_id=d.company_id,
            company_name=company_map.get(d.company_id, ""),
            label=f"{d.filename} · {d.status}", at=d.created_at.isoformat()))
    reports = (db.execute(select(AnalysisReport).where(AnalysisReport.company_id.in_(list(company_map) or [""]))
                          .order_by(desc(AnalysisReport.created_at)).limit(5)).scalars().all())
    for r in reports:
        activity.append(ActivityItemOut(
            kind="report", company_id=r.company_id, company_name=company_map.get(r.company_id, ""),
            label=f"Analysis report · risk {r.overall_risk_score:.0f}/100", at=r.created_at.isoformat()))
    activity.sort(key=lambda a: a.at, reverse=True)

    total_docs = sum(c.document_count for c in cards)
    return DashboardOut(
        companies=company_cards,
        totals={"companies": len(companies), "documents": total_docs, "reports": len(reports)},
        recent_activity=activity[:10],
    )
