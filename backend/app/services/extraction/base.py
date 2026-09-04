"""Common extraction data structures."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExtractedTable:
    page_number: int
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [" | ".join(self.headers)] if self.headers else []
        if self.headers:
            lines.append(" | ".join(["---"] * len(self.headers)))
        for row in self.rows:
            lines.append(" | ".join(row))
        return "\n".join(lines)


@dataclass
class ExtractedPage:
    page_number: int
    text: str
    tables: list[ExtractedTable] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    approximate_page: bool = False


@dataclass
class ExtractionResult:
    pages: list[ExtractedPage]
    parser: str
    page_basis: str = "exact"    # exact | slide | sheet | approximate
    warnings: list[str] = field(default_factory=list)
