"""Synthetic sample documents for the demo company "Aurora Components Ltd.".

100% synthetic, safe to distribute - no real company data. Numbers are crafted
so the deterministic engines demonstrate: revenue growth, rising debt, margin
decline, customer concentration, opportunities, and a cross-document
contradiction (deck claims a diversified customer base; the annual report
reports 44% top-3 concentration).
"""
from __future__ import annotations

from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz

SAMPLE_COMPANY = {
    "name": "Aurora Components Ltd.",
    "ticker": "AURC",
    "industry": "Industrial Manufacturing - Precision Components",
    "country": "United States",
    "description": ("Synthetic demo company. Manufacturer of precision components for "
                    "industrial automation, aerospace and medical devices."),
}

_WIDTH, _HEIGHT = 612, 792  # US Letter
_MARGIN = 64


def _write_pages(path: Path, pages: list[list[str]]) -> None:
    doc = fitz.open()
    for page_lines in pages:
        page = doc.new_page(width=_WIDTH, height=_HEIGHT)
        y = _MARGIN
        for line in page_lines:
            is_title = line.startswith("# ")
            text = line.lstrip("# ")
            page.insert_text((_MARGIN, y), text[:110], fontsize=13 if is_title else 10.5,
                             fontname="helv" if not is_title else "hebo",
                             color=(0.08, 0.13, 0.2))
            y += 26 if is_title else 17
    doc.save(str(path))
    doc.close()


# ---------------------------------------------------------------- FY2025 AR
FY25_AR_PAGES: list[list[str]] = [
    ["# AURORA COMPONENTS LTD.", "Annual Report - Fiscal Year 2025",
     "Precision components for industrial automation, aerospace and medical devices.",
     "This document is a synthetic sample created for demonstration purposes."],
    ["# 1. Business Overview",
     "Aurora Components Ltd. manufactures precision components for industrial automation,",
     "aerospace and medical device customers. Manufacturing operations are located in",
     "the United States, Mexico and Poland.",
     "Customer base: Our top three customers accounted for 44% of revenue in FY2025,",
     "compared with 36% in FY2024. The largest customer, Northline Robotics, represented",
     "21% of FY2025 revenue. Contracts with the top three customers run through 2027."],
    ["# 2. Management Discussion and Analysis",
     "USD millions. Fiscal year ended December 31.",
     "FY2025 revenue was 630.4 compared with 520.8 in FY2024 and 410.2 in FY2023,",
     "growth of 21.0% year over year.",
     "International operations contributed 38% of revenue in FY2025, up from 30% in",
     "FY2024, led by expansion in Central Europe.",
     "Gross margin declined to 37.9% in FY2025 from 40.0% in FY2024, reflecting higher",
     "specialty alloy input costs and startup costs at the Poland facility.",
     "Operating margin declined to 14.0% in FY2025 from 16.0% in FY2024."],
    ["# 3. Risk Factors (excerpt)",
     "Customer concentration: A significant portion of revenue is derived from a small",
     "number of customers. The loss of any major customer could materially affect revenue.",
     "Supplier concentration: We rely on a limited number of suppliers for specialty alloys.",
     "Supply disruptions would negatively impact production schedules and margins.",
     "Cybersecurity: An information security incident could disrupt operations and harm",
     "our reputation. We continue to invest in security controls.",
     "Regulatory: Changing trade regulations and tariffs may affect our international",
     "supply chain and export sales.",
     "Competition: The precision components market is intensely competitive with periodic",
     "pricing pressure from larger diversified competitors."],
    ["# 4. Consolidated Statements of Income",
     "USD millions | FY2023 FY2024 FY2025",
     "Total revenue 410.2 520.8 630.4",
     "Cost of revenues 246.1 312.5 391.2",
     "Gross profit 164.1 208.3 239.2",
     "Research and development 24.6 31.2 39.7",
     "Operating income 61.5 83.3 88.3",
     "Interest expense 6.2 8.9 12.4",
     "Net income 39.8 55.2 58.9"],
    ["# 5. Consolidated Balance Sheets",
     "USD millions | FY2023 FY2024 FY2025",
     "Cash and cash equivalents 88.4 96.2 104.7",
     "Accounts receivable 71.2 83.4 96.8",
     "Inventories 58.3 66.1 74.9",
     "Total current assets 210.5 238.9 261.3",
     "Total current liabilities 131.2 146.3 163.2",
     "Total assets 402.7 461.5 528.4",
     "Total debt 142.0 175.3 230.1",
     "Total liabilities 205.3 246.2 292.7",
     "Shareholders equity 197.4 215.3 235.7"],
    ["# 6. Consolidated Statements of Cash Flows",
     "USD millions | FY2023 FY2024 FY2025",
     "Net cash provided by operating activities 62.4 71.8 74.2",
     "Capital expenditure 18.9 24.6 29.8",
     "Free cash flow 43.5 47.2 44.4"],
    ["# 7. Liquidity and Debt",
     "EBITDA was 97.8 in FY2025 compared with 89.1 in FY2024 and 70.4 in FY2023.",
     "Total debt increased to 230.1 in FY2025 from 175.3 in FY2024, primarily reflecting",
     "a new 60.0 term loan to fund the Poland capacity expansion, drawn in Q2 FY2025.",
     "The term loan matures in FY2030 with quarterly amortization of 3.0.",
     "Management expects to fund repayment from operating cash flow.",
     "Cash and cash equivalents of 104.7 at year end provide additional liquidity."],
    ["# 8. Segment and Geographic Information",
     "FY2025 international revenue was 239.6, or 38% of total revenue.",
     "Revenue by region: Americas 391.3, Europe 201.8, Asia-Pacific 37.3.",
     "Europe revenue growth reflects the new Poland facility ramp."],
    ["# 9. Corporate Governance",
     "The board comprises seven directors, five of whom are independent.",
     "The audit committee reviews the annual operating plan and related-party transactions.",
     "Executive compensation is tied to revenue growth, operating margin and safety metrics.",
     "Outlook: Management expects revenue growth of 10-12% in FY2026 with gradual",
     "gross margin recovery as the Poland facility reaches full utilization."],
]

# ---------------------------------------------------------------- FY2024 AR
FY24_AR_PAGES: list[list[str]] = [
    ["# AURORA COMPONENTS LTD.", "Annual Report - Fiscal Year 2024",
     "Synthetic sample document for demonstration purposes."],
    ["# 1. Business Overview",
     "Our top three customers accounted for 36% of revenue in FY2024.",
     "International operations contributed 30% of revenue in FY2024."],
    ["# 2. Management Discussion and Analysis",
     "USD millions. FY2024 revenue was 520.8 compared with 410.2 in FY2023 and 372.5 in FY2022.",
     "Gross margin was 40.0% in FY2024 and 40.0% in FY2023.",
     "Operating margin was 16.0% in FY2024 and 15.0% in FY2023."],
    ["# 3. Consolidated Statements of Income",
     "USD millions | FY2022 FY2023 FY2024",
     "Total revenue 372.5 410.2 520.8",
     "Cost of revenues 223.5 246.1 312.5",
     "Gross profit 149.0 164.1 208.3",
     "Research and development 20.1 24.6 31.2",
     "Operating income 55.9 61.5 83.3",
     "Interest expense 5.4 6.2 8.9",
     "Net income 34.1 39.8 55.2"],
    ["# 4. Consolidated Balance Sheets",
     "USD millions | FY2022 FY2023 FY2024",
     "Cash and cash equivalents 82.1 88.4 96.2",
     "Accounts receivable 62.0 71.2 83.4",
     "Inventories 51.6 58.3 66.1",
     "Total current assets 187.4 210.5 238.9",
     "Total current liabilities 120.8 131.2 146.3",
     "Total assets 355.9 402.7 461.5",
     "Total debt 128.4 142.0 175.3",
     "Total liabilities 188.1 205.3 246.2",
     "Shareholders equity 167.8 197.4 215.3"],
    ["# 5. Consolidated Statements of Cash Flows",
     "USD millions | FY2022 FY2023 FY2024",
     "Net cash provided by operating activities 54.9 62.4 71.8",
     "Capital expenditure 15.2 18.9 24.6",
     "Free cash flow 39.7 43.5 47.2",
     "EBITDA was 89.1 in FY2024 compared with 70.4 in FY2023 and 63.2 in FY2022."],
    ["# 6. Risk Factors (excerpt)",
     "The precision components market is intensely competitive.",
     "We rely on a limited number of suppliers for specialty alloys."],
]

# ------------------------------------------------- FY2025 Investor Presentation
FY25_DECK_SLIDES: list[list[str]] = [
    ["# AURORA COMPONENTS - INVESTOR PRESENTATION FY2025", "September 2025",
     "Synthetic sample for demonstration purposes."],
    ["# Growth Strategy",
     "Revenue has compounded at 24% annually since FY2023.",
     "We target 15-18% annual revenue growth over the next three years,",
     "driven by international expansion and new automation product lines."],
    ["# Our Customer Base",
     "We serve a highly diversified customer base across 14 industries.",
     "No single end market represents a material share of demand.",
     "Diversification insulates revenue from sector-specific downturns."],
    ["# Margin Trajectory",
     "We expect gross margin to recover toward 40% as the Poland facility ramps.",
     "Operating margin expansion of 100-150 bps per year is targeted from FY2027."],
    ["# Balance Sheet Strength",
     "We maintain a disciplined capital allocation framework.",
     "Recent investments position us to reduce leverage over the medium term."],
    ["# Summary",
     "Aurora combines strong growth with an increasingly global footprint.",
     "Appendix: figures consistent with the FY2025 annual report."],
]

# --------------------------------------------------- FY2025 Earnings Release
FY25_EARNINGS_PAGES: list[list[str]] = [
    ["# AURORA COMPONENTS REPORTS FY2025 RESULTS", "Press Release - Earnings",
     "Synthetic sample for demonstration purposes."],
    ["# FY2025 Highlights",
     "Revenue of 630.4, up 21.0% versus FY2024.",
     "Gross margin of 37.9%; operating margin of 14.0%.",
     "Net income of 58.9; EBITDA of 97.8.",
     "Operating cash flow of 74.2; free cash flow of 44.4.",
     "Top three customers accounted for 44% of FY2025 revenue.",
     "International revenue contributed 38% of total.",
     "Total debt of 230.1 following the Poland expansion facility.",
     "CEO quote: Growth was driven by international expansion and automation demand."],
    ["# FY2026 Guidance",
     "Management guides to revenue of 695-705 (10-12% growth).",
     "Gross margin expected between 38.5% and 39.5%."],
]

SAMPLE_DOCS = [
    ("Aurora_Annual_Report_FY2025.pdf", FY25_AR_PAGES, "annual_report", 2025),
    ("Aurora_Annual_Report_FY2024.pdf", FY24_AR_PAGES, "annual_report", 2024),
    ("Aurora_Investor_Presentation_FY2025.pdf", FY25_DECK_SLIDES, "investor_presentation", 2025),
    ("Aurora_Earnings_Release_FY2025.pdf", FY25_EARNINGS_PAGES, "earnings_report", 2025),
]


def generate_sample_documents(output_dir: Path) -> list[tuple[str, Path, str, int]]:
    """Writes the synthetic PDFs; returns (filename, path, doc_type, fiscal_year)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    produced = []
    for filename, pages, doc_type, year in SAMPLE_DOCS:
        path = output_dir / filename
        _write_pages(path, pages)
        produced.append((filename, path, doc_type, year))
    return produced


# Benchmark Q&A for the offline RAG evaluation harness (expected provenance).
RAG_BENCHMARK = [
    {
        "question": "What was revenue in FY2025?",
        "expected_answer_contains": "630.4",
        "expected_document": "Aurora_Annual_Report_FY2025.pdf",
        "expected_page": 5,
        "expected_evidence": "Total revenue 410.2 520.8 630.4",
    },
    {
        "question": "What percentage of revenue comes from the top three customers?",
        "expected_answer_contains": "44",
        "expected_document": "Aurora_Annual_Report_FY2025.pdf",
        "expected_page": 2,
        "expected_evidence": "top three customers accounted for 44% of revenue",
    },
    {
        "question": "What caused the increase in debt in FY2025?",
        "expected_answer_contains": "Poland",
        "expected_document": "Aurora_Annual_Report_FY2025.pdf",
        "expected_page": 8,
        "expected_evidence": "term loan to fund the Poland capacity expansion",
    },
    {
        "question": "How did gross margin change in FY2025?",
        "expected_answer_contains": "37.9",
        "expected_document": "Aurora_Annual_Report_FY2025.pdf",
        "expected_page": 3,
        "expected_evidence": "Gross margin declined to 37.9% in FY2025 from 40.0%",
    },
    {
        "question": "What was operating cash flow in FY2024?",
        "expected_answer_contains": "71.8",
        "expected_document": "Aurora_Annual_Report_FY2024.pdf",
        "expected_page": 6,
        "expected_evidence": "Net cash provided by operating activities 54.9 62.4 71.8",
    },
]
