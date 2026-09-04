"""PDF extraction + metadata + classification on generated sample documents."""
from app.services.extraction.classifier import classify_document
from app.services.extraction.registry import extract_any


def test_pdf_pages_extracted_with_boundaries(sample_files):
    path = next(p for name, p, _t, _y in sample_files if name == "Aurora_Annual_Report_FY2025.pdf")
    result = extract_any("pdf", str(path))
    assert len(result.pages) == 10
    assert result.pages[0].page_number == 1
    assert "AURORA COMPONENTS LTD." in result.pages[0].text
    assert "Consolidated Statements of Income" in result.pages[4].text


def test_pdf_table_content_preserved_as_text_lines(sample_files):
    """Vector-ruled tables use page.find_tables(); text-drawn tables remain as
    aligned line content, which the financial parser consumes directly."""
    path = next(p for name, p, _t, _y in sample_files if name == "Aurora_Annual_Report_FY2025.pdf")
    result = extract_any("pdf", str(path))
    income_page = result.pages[4]
    assert "Total revenue" in income_page.text
    assert "410.2" in income_page.text and "630.4" in income_page.text


def test_classifier_annual_report():
    doc_type, conf, year = classify_document("Aurora_Annual_Report_FY2025.pdf",
                                             "Annual Report fiscal 2025 revenue")
    assert doc_type == "annual_report"
    assert conf > 0.5
    assert year == 2025


def test_classifier_investor_presentation():
    doc_type, _conf, _y = classify_document("deck.pptx",
                                            "investor presentation growth strategy slides")
    assert doc_type == "investor_presentation"


def test_financial_extraction_from_sample(sample_files):
    from app.services.finance.extractor import extract_financials
    path = next(p for name, p, _t, _y in sample_files if name == "Aurora_Annual_Report_FY2025.pdf")
    result = extract_any("pdf", str(path))
    metrics = extract_financials(result)
    by_key = {(m.metric, m.period_label): m for m in metrics}
    revenue25 = by_key[("total_revenue", "FY2025")]
    assert revenue25.value == pytest_approx(630.4)
    assert revenue25.source_page in (3, 5)
    debt25 = by_key[("total_debt", "FY2025")]
    assert debt25.value == pytest_approx(230.1)
    concentration = by_key[("top3_customer_revenue_pct", "FY2025")]
    assert concentration.value == pytest_approx(44.0)
    assert concentration.source_page == 2
    assert by_key[("ebitda", "FY2025")].value == pytest_approx(97.8)
    assert by_key[("operating_cash_flow", "FY2024")].value == pytest_approx(71.8)


def pytest_approx(expected):
    import pytest
    class _Approx:
        def __eq__(self, other):
            return abs(other - expected) < 0.05
    return _Approx()
