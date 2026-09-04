from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_scoped_company
from app.core.db import get_db
from app.core.errors import NotFoundError
from app.core.jobs import get_job_manager
from app.models import AnalysisReport, Company, User
from app.schemas.report import ReportDetailOut, ReportOut

router = APIRouter(tags=["reports"])


@router.post("/companies/{company_id}/report", response_model=ReportOut, status_code=201)
def generate_report(company_id: str, db: Session = Depends(get_db),
                    company: Company = Depends(get_scoped_company),
                    user: User = Depends(get_current_user)):
    """Runs a full analysis and returns the fresh executive report."""
    from app.services.analysis.orchestrator import run_company_analysis
    report_id = run_company_analysis(db, company)
    report = db.get(AnalysisReport, report_id)
    return ReportOut.model_validate(report)


@router.get("/companies/{company_id}/reports", response_model=list[ReportOut])
def list_reports(company_id: str, db: Session = Depends(get_db),
                 company: Company = Depends(get_scoped_company)):
    reports = (db.query(AnalysisReport).filter(AnalysisReport.company_id == company.id)
               .order_by(desc(AnalysisReport.created_at)).all())
    return [ReportOut.model_validate(r) for r in reports]


def _get_report_scoped(db: Session, report_id: str, user: User) -> AnalysisReport:
    report = db.get(AnalysisReport, report_id)
    if report is None:
        raise NotFoundError("Report not found.")
    company = db.get(Company, report.company_id)
    if company is None or company.user_id != user.id:
        raise NotFoundError("Report not found.")
    return report


@router.get("/reports/{report_id}", response_model=ReportDetailOut)
def get_report(report_id: str, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    report = _get_report_scoped(db, report_id, user)
    detail = ReportDetailOut.model_validate(report)
    detail.content = report.content_json or {}
    return detail


@router.get("/reports/{report_id}/html", response_class=HTMLResponse)
def get_report_html(report_id: str, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    report = _get_report_scoped(db, report_id, user)
    return HTMLResponse(report.content_html or "<html><body><p>Report content unavailable.</p></body></html>")
