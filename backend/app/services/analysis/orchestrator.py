"""Full company analysis pipeline (Evidence -> Analysis -> Generation):

1. verify processed evidence
2. load financial snapshot + ratios
3. run deterministic risk engine
4. run deterministic opportunity engine
5. detect cross-document inconsistencies
6. generate management questions
7. persist everything + executive report
"""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import InsufficientEvidenceError
from app.core.jobs import Job
from app.core.logging import get_logger
from app.models import (
    AnalysisReport, Company, Document, Inconsistency, ManagementQuestion,
    Opportunity, OpportunityEvidence, Risk, RiskEvidence,
)
from app.models.enums import DocumentStatus, RiskSeverity
from app.services.analysis.evidence import chunk_quote_for_patterns, resolve_metric_evidence
from app.services.contradiction.engine import (
    detect_claim_vs_data_inconsistencies, detect_numeric_metric_conflicts,
)
from app.services.finance.service import (
    financial_health_score, growth_potential_score, load_snapshot,
)
from app.services.opportunity.engine import DetectedOpportunity, detect_opportunities
from app.services.questions.engine import generate_questions
from app.services.reports.generator import build_report_content, render_report_html
from app.services.risk.engine import (
    DetectedRisk, overall_risk_score, run_risk_engine,
)

from app.services.reports.generator import SECTION_ORDER as REPORT_SECTION_ORDER
log = get_logger("app.analysis")

STEPS = [
    "Preparing evidence",
    "Analyzing financials",
    "Detecting risks",
    "Finding opportunities",
    "Checking inconsistencies",
    "Generating summary",
]

# qualitative risks visible only in text (rules over numbers cannot see these)
_TEXT_PATTERNS: dict[str, dict] = {
    "supplier_concentration": {
        "patterns": [r"(single|limited|sole)\s+supplier",
                     r"rely\s+on\s+a\s+limited\s+number\s+of\s+suppliers?"],
        "title": "Supplier concentration mentioned in disclosures",
    },
    "cybersecurity": {
        "patterns": [r"cyber ?security", r"data\s+breach", r"information\s+security"],
        "title": "Cybersecurity exposure disclosed",
    },
    "regulatory": {
        "patterns": [r"regulatory\s+compliance", r"changing\s+regulations?", r"trade\s+restrictions?"],
        "title": "Regulatory exposure disclosed",
    },
    "competitive": {
        "patterns": [r"intense(ly)?\s+competitive", r"competitive\s+pressure"],
        "title": "Competitive pressure disclosed",
    },
}


def run_company_analysis(db: Session, company: Company, job: Job | None = None) -> str:
    """Runs the full pipeline; returns the created report id. Persists risks,
    opportunities, inconsistencies, questions and the executive report."""
    settings = get_settings()

    def step(name: str) -> None:
        if job is not None:
            from app.core.jobs import get_job_manager
            get_job_manager().set_step(job, name)

    step("Preparing evidence")
    ready_docs = db.execute(
        select(Document).where(Document.company_id == company.id,
                               Document.status == DocumentStatus.READY.value)
    ).scalars().all()
    if not ready_docs:
        raise InsufficientEvidenceError(
            "No processed (READY) documents available. Upload and process at least one document first.")

    # idempotent re-analysis: clear previous generated findings
    db.execute(delete(RiskEvidence).where(RiskEvidence.risk_id.in_(
        select(Risk.id).where(Risk.company_id == company.id))))
    db.execute(delete(OpportunityEvidence).where(OpportunityEvidence.opportunity_id.in_(
        select(Opportunity.id).where(Opportunity.company_id == company.id))))
    for model in (Risk, Opportunity, Inconsistency, ManagementQuestion):
        db.execute(delete(model).where(model.company_id == company.id))
    db.commit()

    step("Analyzing financials")
    snapshot = load_snapshot(db, company.id)

    # ------------------------------------------------------------- risks
    step("Detecting risks")
    detected_risks: list[DetectedRisk] = run_risk_engine(snapshot, settings)
    evidence_hits: dict[int, tuple[str, int, str]] = {}   # index in list -> (doc, page, quote)

    for category, spec in _TEXT_PATTERNS.items():
        if any(r.category == category for r in detected_risks):
            continue
        hit = chunk_quote_for_patterns(db, company.id, spec["patterns"])
        if hit:
            doc_id, page, quote = hit
            detected_risks.append(DetectedRisk(
                category=category, title=spec["title"], severity=RiskSeverity.MEDIUM,
                score=45.0,
                explanation=f"Company disclosures reference {category.replace('_', ' ')}: \"{quote[:220]}\"",
                why_it_matters="Qualitative disclosures can indicate structural exposures not yet visible in the numbers.",
                potential_impact="Potential operational or financial impact depending on the underlying exposure.",
                recommendation="Investigate the disclosed exposure in the management discussion.",
                confidence="medium", detected_signals={"matched_text": quote[:220]},
            ))
            evidence_hits[len(detected_risks) - 1] = hit

    overall = overall_risk_score(detected_risks)
    persisted_risks: list[Risk] = []
    for idx, detected in enumerate(detected_risks):
        risk_row = Risk(
            company_id=company.id, category=detected.category, title=detected.title,
            severity=detected.severity.value, score=detected.score,
            explanation=detected.explanation, why_it_matters=detected.why_it_matters,
            potential_impact=detected.potential_impact, recommendation=detected.recommendation,
            confidence=detected.confidence, detected_signals=detected.detected_signals,
        )
        db.add(risk_row)
        db.flush()
        persisted_risks.append(risk_row)

        doc_id, page, quote = None, None, detected.evidence_quote
        if idx in evidence_hits:
            doc_id, page, quote = evidence_hits[idx]
        elif detected.evidence_hint_metric:
            doc_id, page, resolved = resolve_metric_evidence(
                db, company.id, detected.evidence_hint_metric, detected.evidence_period)
            quote = quote or resolved
        if doc_id:
            doc = db.get(Document, doc_id)
            db.add(RiskEvidence(risk_id=risk_row.id, document_id=doc_id,
                                document_name=doc.filename if doc else "",
                                page_number=page or 0, section="", quote=(quote or "")[:400]))
    db.commit()

    # ------------------------------------------------------- opportunities
    step("Finding opportunities")
    detected_opps: list[DetectedOpportunity] = detect_opportunities(snapshot)
    persisted_opps: list[Opportunity] = []
    for detected in detected_opps:
        opp_row = Opportunity(
            company_id=company.id, category=detected.category, title=detected.title,
            description=detected.description, potential_impact=detected.potential_impact,
            confidence=detected.confidence,
        )
        db.add(opp_row)
        db.flush()
        persisted_opps.append(opp_row)
        doc_id, page, quote = resolve_metric_evidence(
            db, company.id, detected.evidence_hint_metric, detected.evidence_period)
        if doc_id:
            doc = db.get(Document, doc_id)
            db.add(OpportunityEvidence(opportunity_id=opp_row.id, document_id=doc_id,
                                       document_name=doc.filename if doc else "",
                                       page_number=page or 0, section="", quote=(quote or "")[:400]))
    db.commit()

    # ------------------------------------------------------ inconsistencies
    step("Checking inconsistencies")
    concentration = snapshot.value("top3_customer_revenue_pct")
    inconsistencies = (
        detect_numeric_metric_conflicts(db, company.id)
        + detect_claim_vs_data_inconsistencies(db, company.id, concentration)
    )
    for inc in inconsistencies:
        db.add(Inconsistency(
            company_id=company.id, topic=inc.topic, claim_a=inc.claim_a, claim_b=inc.claim_b,
            source_a_document_id=inc.source_a_document_id, source_a_page=inc.source_a_page,
            source_b_document_id=inc.source_b_document_id, source_b_page=inc.source_b_page,
            explanation=inc.explanation, severity=inc.severity,
        ))
    db.commit()

    # ----------------------------------------------------------- questions
    questions = generate_questions(detected_risks, detected_opps)
    for q in questions:
        db.add(ManagementQuestion(company_id=company.id, topic=q["topic"],
                                  question=q["question"], rationale=q["rationale"],
                                  priority=q["priority"]))
    db.commit()

    # ------------------------------------------------------------ summary
    step("Generating summary")
    narrative = _narrative_summary(company, snapshot, detected_risks, detected_opps, inconsistencies)
    health_score, health_level = financial_health_score(snapshot)
    growth_score, growth_level = growth_potential_score(snapshot)

    content = build_report_content(
        db, company, snapshot, persisted_risks, detected_risks, persisted_opps,
        inconsistencies, questions, narrative,
        overall=overall, health=(health_score, health_level), growth=(growth_score, growth_level),
        documents=ready_docs,
    )
    report = AnalysisReport(
        company_id=company.id,
        period_from=snapshot.periods[0].period_label if snapshot.periods else None,
        period_to=snapshot.latest.period_label if snapshot.latest else None,
        overall_risk_score=overall,
        content_json=content,
        content_html=render_report_html(content),
    )
    db.add(report)
    db.commit()
    log.info("analysis complete", extra={"company_id": company.id, "report_id": report.id,
                                         "processing_status": f"risks={len(persisted_risks)} opps={len(detected_opps)}"})
    return report.id


def _narrative_summary(company: Company, snapshot, risks, opps, inconsistencies) -> dict:
    settings = get_settings()
    fallback = _template_summary(company, snapshot, risks, opps, inconsistencies)
    from app.services.llm.client import get_llm_service
    llm = get_llm_service(settings)
    if llm.available:
        try:
            from app.prompts import templates
            facts = _facts_brief(company, snapshot, risks, opps, inconsistencies)
            raw = llm.complete_json(templates.SUMMARY_SYSTEM, facts, max_tokens=1600)
            if raw:
                # Normalize: accept legacy "overview" key, always return all 13 sections.
                raw = {("company_overview" if k == "overview" else k): v for k, v in raw.items()}
                return {k: raw.get(k) or fallback.get(k, "") for k in REPORT_SECTION_ORDER}
        except Exception as exc:  # noqa: BLE001
            log.warning("LLM summary failed, using template: %s", exc)
    return fallback


def _facts_brief(company: Company, snapshot, risks, opps, inconsistencies) -> str:
    lines = [f"Company: {company.name} ({company.ticker or 'n/a'}, {company.industry or 'n/a'})"]
    for p in snapshot.periods:
        rev = p.values.get("total_revenue")
        ni = p.values.get("net_income")
        debt = p.values.get("total_debt")
        lines.append(f"- {p.period_label}: revenue={rev and round(rev, 1)}, "
                     f"net_income={ni and round(ni, 1)}, debt={debt and round(debt, 1)}")
    latest_label = snapshot.latest.period_label if snapshot.latest else ""
    lines.append(f"- Latest ratios: {snapshot.ratios_by_period.get(latest_label, {})}")
    lines.append("- Risks: " + ("; ".join(f"{r.title} ({r.severity.value})" for r in risks) or "none"))
    lines.append("- Opportunities: " + ("; ".join(o.title for o in opps) or "none"))
    lines.append(f"- Potential cross-document inconsistencies: {len(inconsistencies)}")
    return "\n".join(lines)


def _template_summary(company: Company, snapshot, risks, opps, inconsistencies) -> dict:
    """Deterministic 13-section summary — never uses the LLM for figures."""
    latest = snapshot.latest
    rev = latest.values.get("total_revenue") if latest else None
    rev_line = (f"Revenue of {rev:,.1f} in {latest.period_label}" if latest and rev
                else "Financial data is limited in the current document set.")
    risk_line = "; ".join(r.title for r in risks[:3]) if risks else "no material risks detected by rules"
    opp_line = "; ".join(o.title for o in opps[:3]) if opps else "none detected"
    revenue_series = ", ".join(
        f"{p.period_label}={p.values.get('total_revenue'):,.1f}" for p in snapshot.periods
        if p.values.get("total_revenue") is not None)
    high_risks = [r for r in risks if getattr(r.severity, "value", str(r.severity)) in ("high", "critical")]
    red_flag_bits = [f"{r.title} ({getattr(r.severity, 'value', str(r.severity))})" for r in high_risks[:4]]
    red_flag_bits += [f"Cross-document: {i.topic}" for i in inconsistencies]
    strengths = [o.title for o in opps[:3]]
    return {
        "company_overview": f"{company.name} operates in {company.industry or 'its sector'}. {rev_line} "
                            "Findings are generated from the processed document set.",
        "business_model": "Based on the processed documents; see the cited evidence for details.",
        "financial_performance": f"Revenue trend: {revenue_series or 'not available'}.",
        "financial_health": f"{len(risks)} risk signal(s) detected; key concerns: {risk_line}.",
        "key_strengths": ("Identified growth signals: " + "; ".join(strengths) + ".")
                         if strengths else "No distinct strengths isolated by the current rule set.",
        "key_risks": ("The rule engine flagged: " + risk_line + ".") if risks
                     else "No material risks detected by the deterministic rules.",
        "growth_opportunities": ("Primary opportunities: " + opp_line + ".") if opps
                                else "No opportunities met the detection thresholds.",
        "competitive_position": "Assessment is limited to the available documents.",
        "management_commentary": "See the cross-document analysis and cited management statements.",
        "red_flags": ("Potential red flags: " + "; ".join(red_flag_bits) +
                      ". Further investigation recommended.") if red_flag_bits
                     else "No red flags raised by the current analysis.",
        "inconsistencies": (f"{len(inconsistencies)} potential cross-document inconsistency(ies) "
                            "flagged: " + "; ".join(i.topic for i in inconsistencies) + ".")
                           if inconsistencies else "No cross-document inconsistencies detected.",
        "questions_for_management": ("Focus follow-ups on: " + "; ".join(r.title for r in risks[:3]) + ".")
                                    if risks else "No priority questions generated.",
        "overall_assessment": f"Top opportunities: {opp_line}. "
                              f"{len(inconsistencies)} potential cross-document inconsistency(ies) "
                              "flagged for follow-up.",
    }
