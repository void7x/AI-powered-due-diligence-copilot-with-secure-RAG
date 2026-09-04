"""PDF extraction preserving page boundaries (PyMuPDF). Tables kept structured."""
from __future__ import annotations

try:  # PyMuPDF >= 1.24 prefers the pymupdf name
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz

from app.core.errors import MalformedDocumentError
from app.services.extraction.base import ExtractedPage, ExtractedTable, ExtractionResult


def extract_pdf(path: str) -> ExtractionResult:
    try:
        doc = fitz.open(path)
    except Exception as exc:  # noqa: BLE001
        raise MalformedDocumentError(f"Could not open PDF: {exc}") from exc
    try:
        if doc.is_encrypted:
            raise MalformedDocumentError("Encrypted PDFs are not supported.")
        pages: list[ExtractedPage] = []
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            tables: list[ExtractedTable] = []
            try:
                found = page.find_tables()
                for t in found.tables:
                    table = ExtractedTable(page_number=i, headers=[], rows=[])
                    content = t.extract() or []
                    if content:
                        table.headers = [str(c or "") for c in content[0]]
                        table.rows = [[str(c or "") for c in row] for row in content[1:]]
                    tables.append(table)
            except Exception:  # noqa: BLE001 - table detection is best-effort
                pass
            pages.append(ExtractedPage(page_number=i, text=text, tables=tables,
                                       meta={"char_count": len(text)}))
        if not pages:
            raise MalformedDocumentError("PDF contains no pages.")
        return ExtractionResult(pages=pages, parser="pymupdf", page_basis="exact")
    finally:
        doc.close()
