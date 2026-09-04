"""Extractor registry mapping file kinds to parsers."""
from __future__ import annotations

from app.services.extraction.base import ExtractionResult
from app.services.extraction.office_extractor import extract_docx, extract_pptx
from app.services.extraction.pdf_extractor import extract_pdf
from app.services.extraction.sheet_extractor import extract_csv, extract_txt, extract_xlsx

EXTRACTORS = {
    "pdf": extract_pdf,
    "docx": extract_docx,
    "pptx": extract_pptx,
    "xlsx": extract_xlsx,
    "csv": extract_csv,
    "txt": extract_txt,
}


def extract_any(kind: str, path: str) -> ExtractionResult:
    parser = EXTRACTORS.get(kind)
    if parser is None:
        raise ValueError(f"No extractor registered for '{kind}'")
    return parser(path)
