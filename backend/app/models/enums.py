"""String enums persisted as plain values (portable across PostgreSQL/SQLite)."""
from __future__ import annotations

from enum import Enum


class DocumentStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    EXTRACTING = "EXTRACTING"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    ANALYZING = "ANALYZING"
    READY = "READY"
    FAILED = "FAILED"


class DocumentType(str, Enum):
    ANNUAL_REPORT = "annual_report"
    TEN_K = "10_k"
    TEN_Q = "10_q"
    EARNINGS_REPORT = "earnings_report"
    INVESTOR_PRESENTATION = "investor_presentation"
    FINANCIAL_STATEMENT = "financial_statement"
    MARKET_REPORT = "market_report"
    PRESS_RELEASE = "press_release"
    OTHER = "other"


class RiskSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(str, Enum):
    FINANCIAL = "financial"
    LIQUIDITY = "liquidity"
    LEVERAGE = "leverage"
    CASH_FLOW = "cash_flow"
    MARGIN = "margin"
    CUSTOMER_CONCENTRATION = "customer_concentration"
    SUPPLIER_CONCENTRATION = "supplier_concentration"
    OPERATIONAL = "operational"
    COMPETITIVE = "competitive"
    MARKET = "market"
    REGULATORY = "regulatory"
    LEGAL = "legal"
    GOVERNANCE = "governance"
    CYBERSECURITY = "cybersecurity"
    GEOGRAPHIC = "geographic"
    MANAGEMENT = "management"
    EXECUTION = "execution"


class ClaimType(str, Enum):
    FACT = "fact"
    ANALYSIS = "analysis"
    RECOMMENDATION = "recommendation"
    UNCERTAINTY = "uncertainty"
    CONTRADICTION = "contradiction"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
