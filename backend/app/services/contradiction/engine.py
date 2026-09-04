"""Cross-document inconsistency detection.

Deterministic checks (numeric conflicts + claim-vs-data patterns) with optional
LLM-assisted claim comparison. Language stays neutral: "Potential inconsistency
detected. Further investigation recommended."
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk, FinancialMetric

DIVERSIFIED_PATTERN = re.compile(
    r"(highly\s+)?diversified\s+(customer|revenue)\s+base|broad\s+customer\s+base|"
    r"no\s+single\s+customer[^\n]{0,40}(material|significant)", re.IGNORECASE)
DEBT_DOWN_PATTERN = re.compile(
    r"(reduced|paid\s+down|delevered?|lower)\s+(?:our\s+|total\s+)?(?:debt|leverage|borrowings)", re.IGNORECASE)

PRETTY_METRIC = {
    "top3_customer_revenue_pct": "top-3 customer revenue share",
    "total_debt": "total debt",
    "total_revenue": "revenue",
    "net_income": "net income",
    "international_revenue_pct": "international revenue share",
}


@dataclass
class DetectedInconsistency:
    topic: str
    claim_a: str
    claim_b: str
    source_a_document_id: str | None
    source_a_page: int
    source_b_document_id: str | None
    source_b_page: int
    explanation: str
    severity: str = "medium"


def _doc_label(doc: Document | None) -> str:
    if doc is None:
        return "unknown document"
    year = f" {doc.fiscal_year}" if doc.fiscal_year else ""
    return f"{doc.filename}{year}"


def _scan_chunks(db: Session, company_id: str, pattern: re.Pattern) -> list[tuple[DocumentChunk, re.Match]]:
    hits: list[tuple[DocumentChunk, re.Match]] = []
    chunks = db.execute(
        select(DocumentChunk).where(DocumentChunk.company_id == company_id)
    ).scalars().all()
    for chunk in chunks:
        m = pattern.search(chunk.text)
        if m:
            hits.append((chunk, m))
    return hits


def detect_numeric_metric_conflicts(db: Session, company_id: str,
                                    tolerance: float = 0.02) -> list[DetectedInconsistency]:
    """Same metric, same period, materially different values in different documents."""
    rows = db.execute(select(FinancialMetric).where(FinancialMetric.company_id == company_id)).scalars().all()
    docs = {d.id: d for d in db.execute(select(Document).where(Document.company_id == company_id)).scalars().all()}
    groups: dict[tuple[str, str], list[FinancialMetric]] = {}
    for r in rows:
        if r.source_document_id:
            groups.setdefault((r.period_label, r.metric), []).append(r)
    out: list[DetectedInconsistency] = []
    for (period, metric), items in groups.items():
        by_doc: dict[str, FinancialMetric] = {}
        for item in items:
            if item.source_document_id not in by_doc or item.confidence > by_doc[item.source_document_id].confidence:
                by_doc[item.source_document_id] = item
        distinct = list(by_doc.values())
        if len(distinct) < 2:
            continue
        base = distinct[0]
        for other in distinct[1:]:
            base_v, other_v = base.value, other.value
            if base_v == 0 and other_v == 0:
                continue
            diff = abs(base_v - other_v) / max(abs(base_v), abs(other_v), 1e-9)
            if diff > tolerance:
                pretty = PRETTY_METRIC.get(metric, metric.replace("_", " "))
                out.append(DetectedInconsistency(
                    topic=f"{pretty} ({period})",
                    claim_a=f"{pretty} reported as {base_v:,.1f} for {period}",
                    claim_b=f"{pretty} reported as {other_v:,.1f} for {period}",
                    source_a_document_id=base.source_document_id,
                    source_a_page=base.source_page,
                    source_b_document_id=other.source_document_id,
                    source_b_page=other.source_page,
                    explanation=(f"Potential inconsistency detected: '{pretty}' for {period} differs by "
                                 f"{diff:.0%} between {_doc_label(docs.get(base.source_document_id))} (p.{base.source_page}) "
                                 f"and {_doc_label(docs.get(other.source_document_id))} (p.{other.source_page}). "
                                 "This may reflect different scopes, restatements or definitions. "
                                 "Further investigation recommended."),
                    severity="high" if diff > 0.10 else "medium",
                ))
                break
    return out


def detect_claim_vs_data_inconsistencies(db: Session, company_id: str,
                                         concentration_pct: float | None) -> list[DetectedInconsistency]:
    """Narrative claims vs reported data (e.g. 'diversified base' vs 44% top-3 share)."""
    out: list[DetectedInconsistency] = []
    docs = {d.id: d for d in db.execute(select(Document).where(Document.company_id == company_id)).scalars().all()}

    if concentration_pct is not None and concentration_pct >= 25:
        for chunk, match in _scan_chunks(db, company_id, DIVERSIFIED_PATTERN):
            doc = docs.get(chunk.document_id)
            out.append(DetectedInconsistency(
                topic="customer diversification",
                claim_a=f'Company claims a diversified customer base ("...{match.group(0)}...")',
                claim_b=f"Reported data: top three customers account for {concentration_pct:.0f}% of revenue.",
                source_a_document_id=chunk.document_id,
                source_a_page=chunk.page_number,
                source_b_document_id=_concentration_source(db, company_id),
                source_b_page=_concentration_source_page(db, company_id),
                explanation=("Potential inconsistency detected: the claim of a diversified customer base "
                             "coexists with material reported customer concentration. Companies may define "
                             "'diversified' across industries/geographies rather than revenue share. "
                             "Further investigation recommended."),
                severity="medium" if concentration_pct < 40 else "high",
            ))
            break

    if (debt_trend := _debt_direction(db, company_id)) == "up":
        for chunk, match in _scan_chunks(db, company_id, DEBT_DOWN_PATTERN):
            out.append(DetectedInconsistency(
                topic="deleverage claim",
                claim_a=f'Company claims debt reduction ("...{match.group(0)}...")',
                claim_b="Reported data: total debt increased over the analyzed periods.",
                source_a_document_id=chunk.document_id,
                source_a_page=chunk.page_number,
                source_b_document_id=_metric_doc(db, company_id, "total_debt"),
                source_b_page=_metric_page(db, company_id, "total_debt"),
                explanation=("Potential inconsistency detected: a deleveraging claim alongside rising reported "
                             "total debt. Timing windows or gross-vs-net definitions may differ. "
                             "Further investigation recommended."),
                severity="medium",
            ))
            break
    return out


def _concentration_source(db: Session, company_id: str) -> str | None:
    from sqlalchemy import select as s
    row = db.execute(
        s(FinancialMetric).where(FinancialMetric.company_id == company_id,
                                 FinancialMetric.metric == "top3_customer_revenue_pct")
        .order_by(FinancialMetric.confidence.desc())
    ).scalars().first()
    return row.source_document_id if row else None


def _concentration_source_page(db: Session, company_id: str) -> int:
    from sqlalchemy import select as s
    row = db.execute(
        s(FinancialMetric).where(FinancialMetric.company_id == company_id,
                                 FinancialMetric.metric == "top3_customer_revenue_pct")
        .order_by(FinancialMetric.confidence.desc())
    ).scalars().first()
    return row.source_page if row else 0


def _metric_doc(db: Session, company_id: str, metric: str) -> str | None:
    from sqlalchemy import select as s
    row = db.execute(
        s(FinancialMetric).where(FinancialMetric.company_id == company_id, FinancialMetric.metric == metric)
        .order_by(FinancialMetric.period_label.desc())
    ).scalars().first()
    return row.source_document_id if row else None


def _metric_page(db: Session, company_id: str, metric: str) -> int:
    from sqlalchemy import select as s
    row = db.execute(
        s(FinancialMetric).where(FinancialMetric.company_id == company_id, FinancialMetric.metric == metric)
        .order_by(FinancialMetric.period_label.desc())
    ).scalars().first()
    return row.source_page if row else 0


def _debt_direction(db: Session, company_id: str) -> str | None:
    rows = db.execute(
        select(FinancialMetric).where(FinancialMetric.company_id == company_id,
                                      FinancialMetric.metric == "total_debt")
        .order_by(FinancialMetric.period_label)
    ).scalars().all()
    labels = sorted({r.period_label for r in rows})
    if len(labels) < 2:
        return None
    vals: dict[str, float] = {}
    for r in rows:
        vals[r.period_label] = r.value
    first, last = vals[labels[0]], vals[labels[-1]]
    return "up" if last > first else "down" if last < first else "flat"
