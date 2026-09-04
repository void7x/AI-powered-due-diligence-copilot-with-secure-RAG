"""Chunking: page preservation, sections, overlap, token budgets."""
from app.core.config import get_settings
from app.services.chunking.chunker import DocumentChunker, _blocks_for_page
from app.services.extraction.base import ExtractedPage, ExtractionResult


def _extraction(pages_text: list[str]) -> ExtractionResult:
    return ExtractionResult(pages=[ExtractedPage(page_number=i + 1, text=t)
                                   for i, t in enumerate(pages_text)],
                            parser="test")


def test_pages_are_preserved():
    chunker = DocumentChunker(get_settings())
    drafts = chunker.chunk(_extraction(["Page one text. " * 10, "Page two text. " * 10,
                                        "Page three text. " * 10]))
    assert {d.page_number for d in drafts} == {1, 2, 3}


def test_sections_are_captured():
    text = ("INTRODUCTION\nThis is the intro paragraph with enough content.\n"
            "RISK FACTORS\nWe rely on a limited number of suppliers for specialty alloys.\n"
            "More risk discussion follows here with additional sentences to fill the section.\n")
    chunker = DocumentChunker(get_settings())
    drafts = chunker.chunk(_extraction([text]))
    assert any(d.section == "RISK FACTORS" for d in drafts)
    assert any("suppliers" in d.text for d in drafts)


def test_oversized_piece_is_split_with_budget():
    settings = get_settings()
    settings.chunk_size_tokens = 60
    settings.chunk_overlap_tokens = 15
    chunker = DocumentChunker(settings)
    long_text = " ".join(f"Sentence number {i} adds some more words to the document body."
                         for i in range(80))
    drafts = chunker.chunk(_extraction([long_text]))
    assert len(drafts) > 1
    assert all(d.token_count <= 120 for d in drafts)  # sanity bound


def test_table_marker_becomes_own_block():
    blocks = _blocks_for_page("[TABLE]\nRevenue | 100 | 200\nNet income | 10 | 20\n\nAfter table text.")
    kinds = [k for k, _ in blocks]
    assert "table" in kinds
    table = next(c for k, c in blocks if k == "table")
    assert "Revenue" in table and "Net income" in table


def test_chunk_indices_are_sequential():
    chunker = DocumentChunker(get_settings())
    drafts = chunker.chunk(_extraction(["Alpha beta gamma. " * 30, "Delta epsilon. " * 30]))
    assert [d.chunk_index for d in drafts] == list(range(len(drafts)))
