"""Deterministic financial-data extraction from extracted pages/tables.

Heuristic label+number parser tuned for financial statement layouts:
  Revenue 410.2 520.8 630.4
  USD millions | FY2023 FY2024 FY2025
Values keep value/currency/unit/period/source page - never silently mixed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Document, DocumentPage, FinancialMetric, FinancialPeriod
from app.services.extraction.base import ExtractionResult
from app.utils.text import normalize_ws

# metric -> label patterns (checked in order; first match wins per line)
METRIC_LABELS: dict[str, list[str]] = {
    "total_revenue": [r"total\s+revenue", r"net\s+revenues?", r"^revenues?$", r"net\s+sales", r"total\s+net\s+sales", r"^fy\d{4}\s+revenue\b", r"\brevenue\b(?!\s+(?:growth|share|guidance))"],
    "cogs": [r"costs?\s+of\s+(?:goods\s+)?(?:revenues?|sales|products\s+sold)", r"^cogs$"],
    "gross_profit": [r"gross\s+(?:profit|margin)\b"],
    "operating_income": [r"operating\s+(?:income|profit)", r"income\s+from\s+operations"],
    "ebitda": [r"\bebitda\b"],
    "net_income": [r"net\s+(?:income|profit|earnings)", r"^profit$"],
    "cash": [r"cash\s+and\s+cash\s+equivalents", r"^cash$"],
    "current_assets": [r"total\s+current\s+assets", r"^current\s+assets$"],
    "current_liabilities": [r"total\s+current\s+liabilities", r"^current\s+liabilities$"],
    "total_assets": [r"total\s+assets"],
    "total_liabilities": [r"total\s+liabilities"],
    "total_debt": [r"total\s+debt", r"total\s+(?:long[- ]term\s+)?(?:debt|borrowings)", r"^debt$"],
    "shareholders_equity": [r"total\s+(?:share|stock)holders?['\u2019']?\s+equity", r"shareholders?['\u2019']?\s+equity", r"stockholders?['\u2019']?\s+equity"],
    "operating_cash_flow": [r"net\s+cash\s+(?:provided\s+by|from|used\s+in)\s+operating\s+activities", r"operating\s+cash\s+flow"],
    "capital_expenditure": [r"capital\s+expenditure", r"purchases?\s+of\s+(?:property|pp&e)"],
    "free_cash_flow": [r"free\s+cash\s+flow"],
    "accounts_receivable": [r"accounts?\s+receivable"],
    "inventory": [r"^inventor(?:y|ies)$", r"inventories?\b"],
    "interest_expense": [r"interest\s+expense", r"interest\s+costs?"],
    "rnd_expense": [r"research\s+(?:and|&)\s+development", r"\bR&D\b"],
    "top3_customer_revenue_pct": [r"top\s+(?:three|3)\s+customers?\D{0,40}?(\d+(?:\.\d+)?)\s*%"],
    "international_revenue_pct": [r"international\s+(?:operations?\s+)?(?:contributed|accounted\s+for|revenue\D{0,30})\D{0,30}?(\d+(?:\.\d+)?)\s*%"],
}

_PERIOD_HEADER = re.compile(r"(FY\s?'?\s?(20\d{2}))", re.IGNORECASE)
# narrative series: "EBITDA was 97.8 in FY2025 compared with 89.1 in FY2024"
_NARR_PAIR = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s+in\s+FY(20\d{2})", re.IGNORECASE)
# masks FY mentions so year digits are never parsed as financial values
_FY_MASK = re.compile(r"FY\s?'?\s?(20\d{2})", re.IGNORECASE)
_UNIT_RE = re.compile(r"(in\s+)?(millions?|thousands?|billions?)", re.IGNORECASE)
_CURRENCY_RE = re.compile(r"(USD|EUR|GBP|INR|\$|\u20ac|\u00a3|\u20b9)", re.IGNORECASE)
_NUMBER_RE = re.compile(r"\(?-?\$?\s?\d[\d,]*(?:\.\d+)?\)?%?")


@dataclass
class ExtractedMetric:
    metric: str
    value: float
    currency: str = "USD"
    unit: str = "million"
    period_label: str = ""
    source_page: int = 0
    confidence: float = 0.5
    from_table: bool = False
    quoted_text: str = ""


def _norm_key(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", label.lower()).strip()


def _match_metric(label: str) -> str | None:
    key = _norm_key(label)
    for metric, patterns in METRIC_LABELS.items():
        for pat in patterns:
            if re.search(pat, key, re.IGNORECASE):
                return metric
    return None


def _parse_number(token: str) -> float | None:
    neg = token.startswith("(") and token.endswith(")")
    t = token.strip("()").replace("$", "").replace(",", "").rstrip("%")
    try:
        value = float(t)
    except ValueError:
        return None
    return -value if neg else value


def _unit_multiplier(unit: str) -> float:
    return {"billion": 1000.0, "million": 1.0, "thousand": 0.001}.get(unit, 1.0)


def _detect_unit_and_currency(text: str) -> tuple[str, str]:
    currency = "USD"
    cur_match = _CURRENCY_RE.search(text[:600])
    if cur_match:
        symbol = cur_match.group(1).upper()
        currency = {"$": "USD", "\u20ac": "EUR", "\u00a3": "GBP", "\u20b9": "INR"}.get(symbol, symbol)
    unit = "million"
    if re.search(r"in\s+thousands?|thousands", text[:600], re.IGNORECASE):
        unit = "thousand"
    elif re.search(r"in\s+billions?|billions", text[:600], re.IGNORECASE):
        unit = "billion"
    elif not _UNIT_RE.search(text[:600]):
        unit = "unit"
    return currency, unit


def _periods_from_context(text: str) -> list[str]:
    labels: list[str] = []
    for match in _PERIOD_HEADER.finditer(text):
        label = f"FY{match.group(2)}"
        if label not in labels:
            labels.append(label)
    return labels


def _period_positions(text: str) -> list[tuple[int, str]]:
    """All FY mentions with their offsets, for nearest-before attribution."""
    return [(m.start(2), f"FY{m.group(2)}") for m in _PERIOD_HEADER.finditer(text)]


def _nearest_period_before(positions: list[tuple[int, str]], pos: int, fallback: str = "") -> str:
    before = [label for offset, label in positions if offset <= pos]
    if before:
        return before[-1]
    return fallback


def extract_from_tables(result: ExtractionResult) -> list[ExtractedMetric]:
    out: list[ExtractedMetric] = []
    for page in result.pages:
        page_text = normalize_ws(page.text)
        currency, unit = _detect_unit_and_currency(page_text)
        context_periods = _periods_from_context(page_text)
        for table in page.tables:
            header_periods: list[str] = []
            header_row_idx = -1
            for idx, row in enumerate(table.rows[:4]):
                found = [f"FY{y}" for y in re.findall(r"(20\d{2})", " ".join(row))]
                if len(found) >= 1:
                    header_periods = found
                    header_row_idx = idx
                    break
            periods = header_periods or context_periods
            for row in table.rows:
                if not row:
                    continue
                metric = _match_metric(row[0])
                if not metric:
                    continue
                numbers = []
                for cell in row[1:]:
                    for tok in _NUMBER_RE.findall(cell):
                        value = _parse_number(tok)
                        if value is not None:
                            numbers.append(value)
                if not numbers:
                    continue
                for i, value in enumerate(numbers):
                    label = periods[i] if i < len(periods) else (periods[-1] if periods else "")
                    if not label:
                        continue
                    out.append(ExtractedMetric(
                        metric=metric, value=value * _unit_multiplier(unit), currency=currency,
                        unit=unit, period_label=label, source_page=page.page_number,
                        confidence=0.85, from_table=True,
                        quoted_text=" | ".join(row)[:200],
                    ))
    return out


_PCT_LINE = {
    "top3_customer_revenue_pct": re.compile(
        r"top\s+(?:three|3)\s+customers?[^\d%]{0,60}(\d+(?:\.\d+)?)\s*%", re.IGNORECASE),
    "international_revenue_pct": re.compile(
        r"international\s+(?:operations?\s+)?(?:contributed|accounted\s+for|revenue[^\d%]{0,40})"
        r"[^\d%]{0,40}?(\d+(?:\.\d+)?)\s*%", re.IGNORECASE),
}


def extract_from_text(result: ExtractionResult) -> list[ExtractedMetric]:
    out: list[ExtractedMetric] = []
    for page in result.pages:
        text = page.text
        flat = normalize_ws(text)
        currency, unit = _detect_unit_and_currency(flat)
        positions = _period_positions(flat)
        fallback_period = positions[0][1] if positions else ""
        for metric, pattern in _PCT_LINE.items():
            m = pattern.search(flat)
            if m:
                # prefer a period mention in the same sentence after the value
                # ("...44% of FY2025 revenue"), else the nearest one before
                tail_match = _PERIOD_HEADER.search(flat, m.end(), m.end() + 48)
                if tail_match:
                    period = f"FY{tail_match.group(2)}"
                else:
                    period = _nearest_period_before(positions, m.start(), fallback_period)
                out.append(ExtractedMetric(
                    metric=metric, value=float(m.group(1)), currency=currency, unit="percent",
                    period_label=period, source_page=page.page_number, confidence=0.8,
                    quoted_text=m.group(0)[:200]))
        consumed = 0
        for line in text.splitlines():
            line_start = consumed
            consumed += len(line) + 1
            flat_line = normalize_ws(line)
            if not flat_line or len(flat_line) > 220:
                continue
            if re.search(r"international\s+revenue", flat_line, re.IGNORECASE):
                continue  # geographic split, not total revenue
            # split composite sentences ("Operating cash flow of 74.2; free cash flow of 44.4.")
            segments = [s.strip() for s in flat_line.split(";") if s.strip()] or [flat_line]
            offset_in_line = 0
            for segment in segments:
                seg_start_flat = flat.find(segment, min(line_start, len(flat) - 1))
                label_match = re.match(
                    r"^([A-Za-z][A-Za-z0-9 ,&/()'\-]{2,60}?)(?:\s+[-(]?[$]?[\d,]+(?:\.[\d]+)?\)?%?)",
                    segment)
                if not label_match:
                    offset_in_line += len(segment) + 1
                    continue
                metric = _match_metric(label_match.group(1))
                if metric is None or metric in _PCT_LINE:
                    offset_in_line += len(segment) + 1
                    continue
                seg_positions = positions  # page-level positions
                masked = _FY_MASK.sub("FY ", segment)  # year digits are not values
                numbers = [v for v in (_parse_number(t) for t in _NUMBER_RE.findall(masked))
                           if v is not None]
                numbers = [n for n in numbers if abs(n) < 10_000_000]
                if not numbers:
                    offset_in_line += len(segment) + 1
                    continue
                # percent-only segments are margins, not absolute values
                if "%" in segment and len(numbers) <= 2 and all(
                        t.rstrip().endswith("%") for t in _NUMBER_RE.findall(masked)):
                    offset_in_line += len(segment) + 1
                    continue

                # narrative series: "<Metric> was N in FY2025 compared with M in FY2024 ..."
                pairs = list(_NARR_PAIR.finditer(segment))
                if pairs:
                    pair_values = {_parse_number(pm.group(1)) for pm in pairs}
                    head = _PERIOD_HEADER.sub(" ", segment[: pairs[0].start(1)])
                    lead = re.search(r"FY\s?'?(20\d{2})", segment[: pairs[0].start(1)])
                    if lead:
                        for tok in _NUMBER_RE.findall(head):
                            value = _parse_number(tok)
                            if value is None or value in pair_values:
                                continue
                            out.append(ExtractedMetric(
                                metric=metric, value=value * _unit_multiplier(unit),
                                currency=currency, unit=unit,
                                period_label=f"FY{lead.group(1)}", source_page=page.page_number,
                                confidence=0.7, quoted_text=segment[:200]))
                    for pm in pairs:
                        value = _parse_number(pm.group(1))
                        if value is None:
                            continue
                        out.append(ExtractedMetric(
                            metric=metric, value=value * _unit_multiplier(unit),
                            currency=currency, unit=unit, period_label=f"FY{pm.group(2)}",
                            source_page=page.page_number, confidence=0.7, quoted_text=segment[:200]))
                    offset_in_line += len(segment) + 1
                    continue

                # period mentions within this segment (positions inside the segment)
                seg_positions = [
                    (off, label) for off, label in positions
                    if seg_start_flat <= off < seg_start_flat + len(segment) + 2
                ] if seg_start_flat >= 0 else []
                prior_periods = [label for off, label in positions if off < line_start]

                if len(numbers) == 1:
                    if not seg_positions:
                        offset_in_line += len(segment) + 1
                        continue
                    targets = [seg_positions[-1][1]]
                else:
                    targets = prior_periods
                    if not targets or len(targets) < len(numbers):
                        offset_in_line += len(segment) + 1
                        continue

                for i, value in enumerate(numbers):
                    period = targets[i] if i < len(targets) else (targets[-1] if targets else "")
                    if not period:
                        continue
                    out.append(ExtractedMetric(
                        metric=metric, value=value * _unit_multiplier(unit), currency=currency,
                        unit=unit, period_label=period, source_page=page.page_number,
                        confidence=0.65, quoted_text=segment[:200]))
                offset_in_line += len(segment) + 1
    return out


def extract_financials(result: ExtractionResult) -> list[ExtractedMetric]:
    """Table extraction first, text lines as complement; dedupe per (metric, period, page)."""
    combined = extract_from_tables(result) + extract_from_text(result)
    best: dict[tuple[str, str], ExtractedMetric] = {}
    for m in combined:
        if not m.period_label or m.metric in ("gross_profit",) and m.value == 0:
            continue
        key = (m.metric, m.period_label)
        current = best.get(key)
        if current is None or (m.from_table, m.confidence) > (current.from_table, current.confidence):
            best[key] = m
    return sorted(best.values(), key=lambda m: (m.period_label, m.metric))


# ---------------------------------------------------------------- persistence
def upsert_financials(db: Session, company_id: str, document: Document,
                      metrics: list[ExtractedMetric]) -> tuple[int, int]:
    """Store extraction results as FinancialPeriod + FinancialMetric rows.

    Re-running for the same document replaces its prior contributions.
    Returns (periods_touched, metrics_stored).
    """
    if not metrics:
        return 0, 0
    db.query(FinancialMetric).filter(
        FinancialMetric.company_id == company_id,
        FinancialMetric.source_document_id == document.id,
    ).delete(synchronize_session=False)

    periods: dict[str, FinancialPeriod] = {}
    existing = db.query(FinancialPeriod).filter(FinancialPeriod.company_id == company_id).all()
    for p in existing:
        periods[p.period_label] = p

    stored = 0
    for m in metrics:
        year_match = re.search(r"(20\d{2})", m.period_label)
        if not year_match:
            continue
        label = m.period_label
        period = periods.get(label)
        if period is None:
            period = FinancialPeriod(
                company_id=company_id, period_label=label, fiscal_year=int(year_match.group(1)),
                currency=m.currency, unit=m.unit, source_document_id=document.id,
                confidence=m.confidence,
            )
            db.add(period)
            db.flush()
            periods[label] = period
        db.add(FinancialMetric(
            company_id=company_id, period_id=period.id, period_label=label, metric=m.metric,
            value=m.value, currency=m.currency, unit=m.unit,
            source_document_id=document.id, source_page=m.source_page, confidence=m.confidence,
        ))
        stored += 1
    db.commit()
    return len(periods), stored
