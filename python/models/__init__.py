"""
Data models for the idx-bei investment research platform.

This module defines normalized data models for companies and their financial data.
All financial metrics are stored in a normalized format to handle inconsistencies
in raw scraped data (different field names, units, signs, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


class PeriodType(Enum):
    """Type of financial reporting period."""
    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    TTM = "ttm"  # Trailing Twelve Months


class Unit(Enum):
    """Unit of measurement for financial values."""
    NONE = "none"  # Ratios and percentages
    THOUSANDS = "thousands"
    MILLIONS = "millions"
    BILLIONS = "billions"


class Source(Enum):
    """Data source for financial records."""
    IDX = "idx"
    YAHOO_FINANCE = "yahoo_finance"
    IXBRL = "ixbrl"


@dataclass
class Company:
    """
    Normalized company model.

    Represents a publicly listed Indonesian company (emiten).
    """
    ticker: str  # Stock ticker/code (e.g., "BBCA")
    name: str  # Full company name
    sector: Optional[str] = None
    sub_sector: Optional[str] = None
    industry: Optional[str] = None
    listing_date: Optional[date] = None
    board: Optional[str] = None  # Papan pencatatan: Utama, Akunting, Development

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        self.ticker = self.ticker.upper().strip()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Company):
            return NotImplemented
        return self.ticker == other.ticker

    def __hash__(self) -> int:
        return hash(self.ticker)


@dataclass
class FinancialPeriod:
    """
    Represents a single financial reporting period for a company.

    Each period contains multiple financial metrics (revenue, net income, etc.)
    that belong to the same reporting date.
    """
    id: Optional[int] = None
    ticker: str = ""
    period_end: Optional[date] = None
    period_type: Optional[PeriodType] = None  # Changed from ANNUAL to None for auto-detection
    fiscal_year: Optional[int] = None
    fiscal_period: Optional[int] = None  # 1-4 for quarterly, None for annual
    currency: str = "IDR"
    unit: Unit = Unit.MILLIONS
    source: Source = Source.IDX
    is_restated: bool = False

    # Raw data reference (for audit trail)
    original_data: dict = field(default_factory=dict)

    # Timestamps
    ingested_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        # Handle string dates
        if self.period_end and isinstance(self.period_end, str):
            try:
                self.period_end = date.fromisoformat(self.period_end)
            except (ValueError, TypeError):
                pass

        if self.period_end and self.fiscal_year is None:
            self.fiscal_year = self.period_end.year

        # Auto-detect period type if not explicitly set
        if self.period_end and self.period_type is None:
            month = self.period_end.month
            if month in (3, 6, 9, 12):
                self.period_type = PeriodType.QUARTERLY
            else:
                self.period_type = PeriodType.ANNUAL

        # Ensure period_type is set (fallback to ANNUAL)
        if self.period_type is None:
            self.period_type = PeriodType.ANNUAL

        if self.period_type == PeriodType.QUARTERLY and self.fiscal_period is None:
            # Infer quarter from month
            if self.period_end:
                month = self.period_end.month
                if month <= 3:
                    self.fiscal_period = 1
                elif month <= 6:
                    self.fiscal_period = 2
                elif month <= 9:
                    self.fiscal_period = 3
                else:
                    self.fiscal_period = 4

    @property
    def period_label(self) -> str:
        """Human-readable label for the period (e.g., '2024-Q2')."""
        if self.period_type == PeriodType.ANNUAL:
            return f"{self.fiscal_year}"
        elif self.period_type == PeriodType.QUARTERLY:
            return f"{self.fiscal_year}-Q{self.fiscal_period}"
        elif self.period_type == PeriodType.TTM:
            end = self.period_end.strftime("%Y-%m-%d") if self.period_end else "unknown"
            return f"TTM-{end}"
        return "unknown"

    def __repr__(self) -> str:
        return f"FinancialPeriod(ticker={self.ticker}, period={self.period_label})"


# Type alias for normalized financial values
# All absolute values are stored in the company's base unit (typically millions IDR)
FinancialValue = Optional[float]


@dataclass
class FinancialMetrics:
    """
    Normalized financial metrics for a single reporting period.

    All absolute values are stored as floats representing the value in the
    period's base unit (typically millions of local currency).
    Ratios and percentages are stored as-is (unit=NONE).
    """
    # Income Statement
    revenue: FinancialValue = None  # sales/revenue
    cost_of_goods_sold: FinancialValue = None
    gross_profit: FinancialValue = None
    operating_income: FinancialValue = None  # ebt (earnings before tax) is sometimes used
    interest_expense: FinancialValue = None
    tax_expense: FinancialValue = None
    net_income: FinancialValue = None  # profit_attr_owner (profit attributable to owner)
    net_income_non_controlling: FinancialValue = None
    eps: FinancialValue = None

    # Balance Sheet
    total_assets: FinancialValue = None
    current_assets: FinancialValue = None
    cash_and_equivalents: FinancialValue = None
    total_liabilities: FinancialValue = None
    current_liabilities: FinancialValue = None
    long_term_debt: FinancialValue = None
    total_debt: FinancialValue = None  # current + long term
    total_equity: FinancialValue = None
    book_value_per_share: FinancialValue = None

    # Cash Flow (to be added in future phases)
    operating_cash_flow: FinancialValue = None
    capital_expenditures: FinancialValue = None
    free_cash_flow: FinancialValue = None

    # Per-share and market data
    shares_outstanding: FinancialValue = None
    dividend_per_share: FinancialValue = None

    # Ratios (unitless, stored as decimals where applicable)
    gross_margin: FinancialValue = None
    operating_margin: FinancialValue = None
    net_margin: FinancialValue = None  # npm
    roe: FinancialValue = None
    roa: FinancialValue = None
    roic: FinancialValue = None  # Return on Invested Capital
    debt_to_equity: FinancialValue = None  # de_ratio
    current_ratio: FinancialValue = None
    pe_ratio: FinancialValue = None  # per
    pb_ratio: FinancialValue = None  # price_bv
    ev_ebitda: FinancialValue = None

    # Growth rates (CAGR)
    revenue_cagr_3y: FinancialValue = None
    revenue_cagr_5y: FinancialValue = None
    earnings_cagr_3y: FinancialValue = None
    earnings_cagr_5y: FinancialValue = None
    eps_cagr_3y: FinancialValue = None
    eps_cagr_5y: FinancialValue = None

    # Metadata
    period_id: Optional[int] = None
    source: str = "idx"

    def is_empty(self) -> bool:
        """Check if all metrics are None."""
        # Only check data attributes, not methods
        data_attrs = [
            'revenue', 'cost_of_goods_sold', 'gross_profit', 'operating_income',
            'interest_expense', 'tax_expense', 'net_income', 'net_income_non_controlling',
            'eps', 'total_assets', 'current_assets', 'cash_and_equivalents',
            'total_liabilities', 'current_liabilities', 'long_term_debt',
            'total_debt', 'total_equity', 'book_value_per_share',
            'operating_cash_flow', 'capital_expenditures', 'free_cash_flow',
            'shares_outstanding', 'dividend_per_share',
            'gross_margin', 'operating_margin', 'net_margin', 'roe', 'roa', 'roic',
            'debt_to_equity', 'current_ratio', 'pe_ratio', 'pb_ratio', 'ev_ebitda',
            'revenue_cagr_3y', 'revenue_cagr_5y',
            'earnings_cagr_3y', 'earnings_cagr_5y',
            'eps_cagr_3y', 'eps_cagr_5y'
        ]
        return all(getattr(self, attr) is None for attr in data_attrs)

    def get_filled_metrics(self) -> dict:
        """Return dict of metric_name -> value for non-None metrics."""
        return {
            attr: getattr(self, attr)
            for attr in dir(self)
            if not attr.startswith('_')
            and attr not in ('period_id', 'source', 'is_empty', 'get_filled_metrics')
            and getattr(self, attr) is not None
        }

    def __repr__(self) -> str:
        filled = len(self.get_filled_metrics())
        return f"FinancialMetrics({filled} metrics filled)"
