"""Automatic document-type classification from filename + content signals."""
from __future__ import annotations

import re

from app.models.enums import DocumentType

_RULES: list[tuple[DocumentType, str]] = [
    (DocumentType.ANNUAL_REPORT, r"annual\s*report"),
    (DocumentType.TEN_K, r"\b10-?k\b"),
    (DocumentType.TEN_Q, r"\b10-?q\b"),
    (DocumentType.EARNINGS_REPORT, r"earnings|quarterly\s+results|q[1-4]\s*20\d\d\s+results"),
    (DocumentType.INVESTOR_PRESENTATION, r"investor\s+(presentation|deck)|presentation"),
    (DocumentType.FINANCIAL_STATEMENT, r"financial\s+statements?|balance\s+sheet|income\s+statement"),
    (DocumentType.MARKET_REPORT, r"market\s+report|industry\s+outlook|research\s+report"),
    (DocumentType.PRESS_RELEASE, r"press\s+release|news\s+release"),
]

_FY_RE = re.compile(r"(?:FY\s?|fiscal\s+(?:year\s+)?)?(20\d{2})", re.IGNORECASE)


def classify_document(filename: str, text_sample: str) -> tuple[str, float, int | None]:
    """Returns (document_type, confidence, fiscal_year_guess)."""
    haystack = f"{filename}\n{text_sample[:4000]}".lower()
    best_type, best_score = DocumentType.OTHER.value, 0.0
    for doc_type, pattern in _RULES:
        matches = len(re.findall(pattern, haystack))
        if matches and matches > best_score:
            best_type, best_score = doc_type.value, float(matches)
    confidence = min(0.95, 0.5 + 0.15 * best_score) if best_score else 0.3

    year: int | None = None
    m = re.search(r"\bFY\s?'?(20\d{2})\b", haystack, re.IGNORECASE) or re.search(
        r"\bfiscal\s+(?:year\s+)?(20\d{2})\b", haystack, re.IGNORECASE)
    if m:
        year = int(m.group(1))
    else:
        years = [int(y) for y in _FY_RE.findall(haystack)]
        if years:
            year = max(years)
    return best_type, confidence, year
