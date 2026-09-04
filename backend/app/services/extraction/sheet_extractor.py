"""XLSX / CSV extraction: one pseudo-page per sheet or row-block, tables structured."""
from __future__ import annotations

import csv

from app.core.errors import MalformedDocumentError
from app.services.extraction.base import ExtractedPage, ExtractedTable, ExtractionResult

_ROWS_PER_PAGE = 60


def extract_xlsx(path: str) -> ExtractionResult:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001
        raise MalformedDocumentError(f"Could not open XLSX: {exc}") from exc
    pages: list[ExtractedPage] = []
    for ws in wb.worksheets:
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        rows = [[("" if v is None else str(v)) for v in row] for row in rows if any(v is not None for v in row)]
        if not rows:
            continue
        for block_no, start in enumerate(range(0, len(rows), _ROWS_PER_PAGE), start=1):
            block = rows[start : start + _ROWS_PER_PAGE]
            table = ExtractedTable(page_number=len(pages) + 1, headers=block[0], rows=block[1:])
            text = f"Sheet: {ws.title} (rows {start + 1}-{start + len(block)})\n" + table.to_markdown()
            pages.append(ExtractedPage(page_number=len(pages) + 1, text=text,
                                       tables=[table], meta={"sheet": ws.title}))
    wb.close()
    if not pages:
        raise MalformedDocumentError("XLSX contains no data rows.")
    return ExtractionResult(pages=pages, parser="openpyxl", page_basis="sheet")


def extract_csv(path: str) -> ExtractionResult:
    try:
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
            rows = [row for row in csv.reader(fh)]
    except Exception as exc:  # noqa: BLE001
        raise MalformedDocumentError(f"Could not parse CSV: {exc}") from exc
    rows = [r for r in rows if any(c.strip() for c in r)]
    if not rows:
        raise MalformedDocumentError("CSV contains no data rows.")
    pages: list[ExtractedPage] = []
    for block_no, start in enumerate(range(0, len(rows), _ROWS_PER_PAGE), start=1):
        block = rows[start : start + _ROWS_PER_PAGE]
        table = ExtractedTable(page_number=block_no, headers=block[0], rows=block[1:])
        text = table.to_markdown()
        pages.append(ExtractedPage(page_number=block_no, text=text, tables=[table], meta={"sheet": "csv"}))
    return ExtractionResult(pages=pages, parser="csv", page_basis="sheet")


def extract_txt(path: str) -> ExtractionResult:
    try:
        raw = open(path, encoding="utf-8-sig", errors="replace").read()
    except Exception as exc:  # noqa: BLE001
        raise MalformedDocumentError(f"Could not read text file: {exc}") from exc
    if not raw.strip():
        raise MalformedDocumentError("Text file is empty.")
    import math
    n_pages = max(1, math.ceil(len(raw) / 2400))
    pages = []
    for i in range(n_pages):
        chunk = raw[i * 2400 : (i + 1) * 2400]
        pages.append(ExtractedPage(page_number=i + 1, text=chunk,
                                   meta={"char_count": len(chunk)}, approximate_page=True))
    return ExtractionResult(pages=pages, parser="plaintext", page_basis="approximate")
