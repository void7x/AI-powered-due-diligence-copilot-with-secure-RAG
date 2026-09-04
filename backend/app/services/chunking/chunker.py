"""Document-aware, section-preserving chunking with token budgets and overlap.

Page numbers, sections and tables survive into every chunk so retrieval
results always carry full provenance (document, page, section, fiscal year).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.config import Settings
from app.services.extraction.base import ExtractionResult
from app.utils.text import approx_tokens, sentence_split

_HEADING_RE = re.compile(
    r"^(?:#{1,4}\s+\S.*"                      # markdown-ish headings
    r"|\d+(?:\.\d+)*[.)]?\s+[A-Z].{2,90}"     # numbered headings: 3.1 Risk Factors
    r"|[A-Z][A-Z0-9 ,&/().'-]{4,90})$"        # ALL-CAPS headings
)
_TABLE_MARK = "[TABLE]"


@dataclass
class ChunkDraft:
    text: str
    page_number: int
    section: str
    chunk_index: int = 0
    token_count: int = 0


def _is_heading(line: str) -> bool:
    s = line.strip()
    if not s or len(s) > 100 or s.startswith(_TABLE_MARK):
        return False
    if s.endswith((".", ";", ",")) and not s.startswith("#"):
        return False
    return bool(_HEADING_RE.match(s))


def _blocks_for_page(text: str) -> list[tuple[str, str]]:
    """Yield (kind, content) blocks: heading | paragraph | table."""
    blocks: list[tuple[str, str]] = []
    paragraph: list[str] = []
    table_lines: list[str] | None = None

    def close_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            blocks.append(("paragraph", " ".join(paragraph)))
            paragraph = []

    def close_table() -> None:
        nonlocal table_lines
        if table_lines and len(table_lines) > 1:
            blocks.append(("table", "\n".join(table_lines)))
        table_lines = None

    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith(_TABLE_MARK):
            close_paragraph()
            close_table()
            table_lines = []
            continue
        if table_lines is not None:
            if stripped:
                table_lines.append(stripped)
                continue
            close_table()
            continue
        if not stripped:
            close_paragraph()
            continue
        if _is_heading(stripped):
            close_paragraph()
            blocks.append(("heading", stripped.lstrip("# ").strip()))
            continue
        paragraph.append(stripped)
    close_table()
    close_paragraph()
    return blocks


class DocumentChunker:
    def __init__(self, settings: Settings) -> None:
        self.size_tokens = settings.chunk_size_tokens
        self.overlap_tokens = max(0, settings.chunk_overlap_tokens)

    # ------------------------------------------------------------------ pack
    def _emit(self, text: str, page_number: int, section: str, out: list[ChunkDraft]) -> None:
        text = text.strip()
        if text:
            out.append(ChunkDraft(text=text, page_number=page_number, section=section,
                                  token_count=approx_tokens(text)))

    def _overlap_from(self, text: str) -> list[str]:
        """Last few sentences of `text`, up to the overlap budget."""
        if self.overlap_tokens <= 0:
            return []
        overlap: list[str] = []
        total = 0
        for sent in reversed(sentence_split(text)):
            total += approx_tokens(sent)
            overlap.insert(0, sent)
            if total >= self.overlap_tokens:
                break
        return overlap

    def _pack(self, pieces: list[str], section: str, page_number: int, out: list[ChunkDraft]) -> None:
        buffer: list[str] = []
        buffer_tokens = 0

        def flush(keep_overlap: bool = False) -> None:
            nonlocal buffer, buffer_tokens
            if not buffer:
                return
            self._emit("\n".join(buffer), page_number, section, out)
            if keep_overlap:
                tail = self._overlap_from(buffer[-1])
                buffer = ["\n".join(tail)] if tail else []
                buffer_tokens = sum(approx_tokens(t) for t in buffer)
            else:
                buffer, buffer_tokens = [], 0

        for piece in pieces:
            piece_tokens = approx_tokens(piece)
            if piece_tokens > self.size_tokens:
                flush()
                self._pack_oversized(piece, section, page_number, out)
                continue
            if buffer and buffer_tokens + piece_tokens > self.size_tokens:
                flush(keep_overlap=True)
            buffer.append(piece)
            buffer_tokens += piece_tokens
        flush()

    def _pack_oversized(self, piece: str, section: str, page_number: int, out: list[ChunkDraft]) -> None:
        chunk: list[str] = []
        chunk_tokens = 0
        for sent in sentence_split(piece):
            st = approx_tokens(sent)
            if chunk and chunk_tokens + st > self.size_tokens:
                overlap = self._overlap_from(" ".join(chunk))
                self._emit(" ".join(chunk), page_number, section, out)
                chunk, chunk_tokens = list(overlap), sum(approx_tokens(s) for s in overlap)
            chunk.append(sent)
            chunk_tokens += st
        self._emit(" ".join(chunk), page_number, section, out)

    # ------------------------------------------------------------------ main
    def chunk(self, extraction: ExtractionResult, document_name: str = "") -> list[ChunkDraft]:
        drafts: list[ChunkDraft] = []
        for page in extraction.pages:
            section = ""
            pieces: list[str] = []
            for kind, content in _blocks_for_page(page.text):
                if kind == "heading":
                    if pieces:
                        self._pack(pieces, section, page.page_number, drafts)
                        pieces = []
                    section = content[:120]
                    pieces.append(f"[Section: {section}]")
                    continue
                if kind == "table":
                    pieces.append(f"[Table - section: {section or 'n/a'}]\n{content}")
                else:
                    pieces.append(content)
            if pieces:
                self._pack(pieces, section, page.page_number, drafts)
        for i, d in enumerate(drafts):
            d.chunk_index = i
        return drafts
