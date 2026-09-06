"""Executive due-diligence report assembly + printable HTML rendering."""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape

from sqlalchemy.orm import Session

from app.models import Company, Document
from app.services.finance.service import FinancialSnapshot

DISCLAIMER = ("This tool provides analytical assistance based on available documents and should "
              "not be treated as financial, legal, tax, or investment advice.")

SECTION_ORDER = [
    "company_overview", "business_model", "financial_performance", "financial_health",
    "key_strengths", "key_risks", "growth_opportunities", "competitive_position",
    "management_commentary", "red_flags", "inconsistencies", "questions_for_management",
    "overall_assessment",
]

SECTION_TITLES = {
    "company_overview": "Company Overview",
    "business_model": "Business Model",
    "financial_performance": "Financial Performance",
    "financial_health": "Financial Health",
    "key_strengths": "Key Strengths",
    "key_risks": "Key Risks",
    "growth_opportunities": "Growth Opportunities",
    "competitive_position": "Competitive Position",
    "management_commentary": "Management Commentary",
    "red_flags": "Potential Red Flags",
    "inconsistencies": "Cross-Document Inconsistencies",
    "questions_for_management": "Key Questions for Management",
    "overall_assessment": "Overall Assessment",
}


def build_report_content(db: Session, company: Company, snapshot: FinancialSnapshot,
                         risk_rows, detected_risks, opportunities, inconsistencies,
                         questions, narrative: dict, *, overall: float,
                         health: tuple[int, str], growth: tuple[int, str],
                         documents: list[Document]) -> dict:
    now = datetime.now(timezone.utc)
    from app.models import OpportunityEvidence, RiskEvidence

    financial_table = []
    for p in snapshot.periods:
        ratios = snapshot.ratios_by_period.get(p.period_label, {})
        financial_table.append({
            "period": p.period_label,
            "revenue": p.values.get("total_revenue"),
            "gross_margin": ratios.get("gross_margin"),
            "operating_margin": ratios.get("operating_margin"),
            "net_income": p.values.get("net_income"),
            "ebitda": p.values.get("ebitda"),
            "total_debt": p.values.get("total_debt"),
            "cash": p.values.get("cash"),
            "operating_cash_flow": p.values.get("operating_cash_flow"),
            "free_cash_flow": p.values.get("free_cash_flow"),
        })
    risk_evidence: dict[str, list] = {}
    for ev in db.query(RiskEvidence).filter(
            RiskEvidence.risk_id.in_([r.id for r in risk_rows])).all() if risk_rows else []:
        risk_evidence.setdefault(ev.risk_id, []).append(ev)
    opp_evidence: dict[str, list] = {}
    opp_ids = [getattr(o, "id", None) for o in opportunities]
    opp_ids = [i for i in opp_ids if i]
    for ev in db.query(OpportunityEvidence).filter(
            OpportunityEvidence.opportunity_id.in_(opp_ids)).all() if opp_ids else []:
        opp_evidence.setdefault(ev.opportunity_id, []).append(ev)

    return {
        "title": "Executive Due Diligence Summary",
        "company": {"id": company.id, "name": company.name, "ticker": company.ticker,
                     "industry": company.industry, "country": company.country},
        "generated_at": now.isoformat(),
        "documents_analyzed": [{"id": d.id, "filename": d.filename,
                                 "type": d.document_type, "fiscal_year": d.fiscal_year}
                                for d in documents],
        "scores": {"overall_risk": overall, "financial_health": health,
                    "growth_potential": growth},
        "narrative": narrative,
        "financial_table": financial_table,
        "risks": [{
            "category": row.category, "title": row.title, "severity": row.severity,
            "score": row.score, "explanation": row.explanation,
            "why_it_matters": row.why_it_matters, "potential_impact": row.potential_impact,
            "recommendation": row.recommendation,
            "evidence": [{"document_id": e.document_id, "document_name": e.document_name,
                          "page_number": e.page_number, "quote": e.quote}
                         for e in risk_evidence.get(row.id, [])],
        } for row in risk_rows],
        "opportunities": [{
            "id": getattr(o, "id", None),
            "category": o.category, "title": o.title, "description": o.description,
            "potential_impact": o.potential_impact, "confidence": o.confidence,
            "evidence": [{"document_id": e.document_id, "document_name": e.document_name,
                          "page_number": e.page_number, "quote": e.quote}
                         for e in opp_evidence.get(getattr(o, "id", ""), [])],
        } for o in opportunities],
        "inconsistencies": [{
            "topic": i.topic, "claim_a": i.claim_a, "claim_b": i.claim_b,
            "source_a_document_id": i.source_a_document_id, "source_a_page": i.source_a_page,
            "source_b_document_id": i.source_b_document_id, "source_b_page": i.source_b_page,
            "explanation": i.explanation, "severity": i.severity,
        } for i in inconsistencies],
        "questions": list(questions),
        "disclaimer": DISCLAIMER,
    }


def render_report_html(content: dict) -> str:
    """Standalone printable HTML with all dynamic text HTML-escaped."""
    company = content.get("company", {})
    scores = content.get("scores", {})
    rows_html = ""
    for row in content.get("financial_table", []):
        def fmt(v, suffix=""):
            return f"{v:,.1f}{suffix}" if isinstance(v, (int, float)) else "—"
        period = escape(str(row.get("period", "")))
        rows_html += (
            f"<tr><td><b>{period}</b></td>"
            f"<td>{fmt(row.get('revenue'))}</td>"
            f"<td>{fmt(row.get('gross_margin'), '%')}</td>"
            f"<td>{fmt(row.get('operating_margin'), '%')}</td>"
            f"<td>{fmt(row.get('net_income'))}</td>"
            f"<td>{fmt(row.get('ebitda'))}</td>"
            f"<td>{fmt(row.get('total_debt'))}</td>"
            f"<td>{fmt(row.get('operating_cash_flow'))}</td></tr>"
        )

    risk_items = ""
    for r in content.get("risks", []):
        sev = escape(str((r.get("severity") or "medium").upper()))
        safe_class = str(r.get("severity") or "medium").lower().replace("_", "-")
        risk_items += (
            f"<li><b>{escape(str(r.get('title') or ''))}</b> <span class='sev sev-{escape(safe_class)}'>{sev}</span><br/>"
            f"<i>What we found:</i> {escape(str(r.get('explanation') or ''))}<br/>"
            f"<i>Why it matters:</i> {escape(str(r.get('why_it_matters') or ''))}<br/>"
            f"<i>What to investigate:</i> {escape(str(r.get('recommendation') or ''))}</li>"
        )

    opp_items = "".join(
        f"<li><b>{escape(str(o.get('title') or ''))}</b> <span class='conf'>{escape(str(o.get('confidence') or ''))}</span><br/>"
        f"{escape(str(o.get('description') or ''))}</li>"
        for o in content.get("opportunities", []))

    inc_items = "".join(
        f"<li><b>{escape(str(i.get('topic') or ''))}</b><br/>A: {escape(str(i.get('claim_a') or ''))}<br/>B: {escape(str(i.get('claim_b') or ''))}<br/>"
        f"<i>{escape(str(i.get('explanation') or ''))}</i></li>"
        for i in content.get("inconsistencies", [])) or "<li>None detected.</li>"

    q_items = "".join(
        f"<li>{escape(str(q.get('question') or ''))} <span class='prio'>[{escape(str(q.get('priority') or ''))}]</span></li>"
        for q in content.get("questions", []))

    docs_items = "".join(
        f"<li>{escape(str(d.get('filename') or ''))} ({escape(str(d.get('type') or ''))}, {escape(str(d.get('fiscal_year') or 'n/a'))})</li>"
        for d in content.get("documents_analyzed", []))

    narrative = content.get("narrative", {})
    sections_html = ""
    for key in SECTION_ORDER:
        body = narrative.get(key, "")
        if not body:
            continue
        sections_html += f"<h2>{escape(SECTION_TITLES.get(key, key))}</h2><p>{escape(str(body))}</p>"

    company_name = escape(str(company.get("name", "")))
    ticker = escape(str(company.get("ticker") or "unlisted"))
    industry = escape(str(company.get("industry") or "n/a"))
    country = escape(str(company.get("country") or "n/a"))
    generated = escape(str(content.get("generated_at", ""))[:19].replace("T", " "))
    overall = escape(str(scores.get("overall_risk", 0)))
    health = scores.get("financial_health", ("-",))
    growth = scores.get("growth_potential", ("-",))
    health_score = escape(str(health[0] if health else "-"))
    growth_score = escape(str(growth[0] if growth else "-"))
    disclaimer = escape(str(content.get("disclaimer", DISCLAIMER)))
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<title>Due Diligence Report - {company_name}</title>
<style>
  body {{ font-family: Georgia, 'Times New Roman', serif; color: #1a2332; max-width: 860px;
         margin: 40px auto; padding: 0 24px; line-height: 1.55; }}
  h1 {{ font-size: 26px; border-bottom: 3px solid #14304f; padding-bottom: 8px; }}
  h2 {{ font-size: 18px; color: #14304f; margin-top: 28px; border-bottom: 1px solid #d7dee8; padding-bottom: 4px; }}
  table {{ border-collapse: collapse; width: 100%; font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 12.5px; }}
  th, td {{ border: 1px solid #ccd5e0; padding: 6px 9px; text-align: right; }}
  th {{ background: #f0f4f9; }} td:first-child, th:first-child {{ text-align: left; }}
  .meta {{ color: #5a6a7e; font-size: 13px; font-family: 'Helvetica Neue', Arial, sans-serif; }}
  .sev {{ font-size: 11px; padding: 1px 8px; border-radius: 3px; font-family: Arial, sans-serif; color: white; }}
  .sev-high, .sev-critical {{ background: #b91c1c; }} .sev-medium {{ background: #b45309; }} .sev-low {{ background: #15803d; }}
  .conf, .prio {{ color: #5a6a7e; font-size: 12px; }}
  .disclaimer {{ margin-top: 36px; padding: 10px 14px; background: #f6f8fb; border-left: 3px solid #8aa0b8;
                 font-size: 12px; color: #4a5a6e; }}
  ul {{ padding-left: 20px; }} li {{ margin-bottom: 8px; }}
  @media print {{ body {{ margin: 10mm auto; }} }}
</style></head><body>
<h1>Executive Due Diligence Summary</h1>
<p class="meta"><b>{company_name}</b> ({ticker} · {industry}, {country})<br/>
Overall risk score: {overall} · Financial health: {health_score} / 100 ·
Growth potential: {growth_score} / 100<br/>
Generated {generated} UTC</p>
<h2>Documents Analyzed</h2><ul>{docs_items}</ul>
{sections_html}
<h2>Financial Summary</h2>
<table><thead><tr><th>Period</th><th>Revenue</th><th>Gross m.</th><th>Op. m.</th><th>Net income</th>
<th>EBITDA</th><th>Total debt</th><th>OCF</th></tr></thead><tbody>{rows_html}</tbody></table>
<h2>Key Risks</h2><ul>{risk_items or '<li>None detected.</li>'}</ul>
<h2>Growth Opportunities</h2><ul>{opp_items or '<li>None detected.</li>'}</ul>
<h2>Cross-Document Inconsistencies</h2><ul>{inc_items}</ul>
<h2>Key Questions for Management</h2><ul>{q_items}</ul>
<p class="disclaimer">{disclaimer}</p>
</body></html>"""
