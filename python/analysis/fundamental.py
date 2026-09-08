"""
Fundamental Analysis Engine for idx-bei.

This module provides deterministic calculations for fundamental analysis metrics.
All calculations are purely mathematical — no AI/LLM involvement.

Metrics are categorized into:
- Growth (CAGR calculations)
- Profitability (margins, ROE, ROA, ROIC)
- Financial Health (leverage, liquidity, coverage)
- Cash Flow (FCF, FCF margin)

Each function handles:
- Missing data (returns None)
- Division by zero (returns None)
- Unit consistency (assumes consistent units within calculation)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Tuple

from models import FinancialMetrics, FinancialPeriod, PeriodType

# Type alias for optional float values used in calculations
FloatVal = Optional[float]


@dataclass
class MetricResult:
    """
    Result of a fundamental metric calculation.

    Contains the calculated value along with metadata about the calculation.
    """
    value: Optional[float]
    metric_name: str
    period: Optional[str] = None
    formula: str = ""
    notes: str = ""

    @property
    def is_available(self) -> bool:
        """Check if the metric has a valid calculated value."""
        return self.value is not None

    def __repr__(self) -> str:
        val_str = f"{self.value:.4f}" if self.value is not None else "N/A"
        return f"MetricResult({self.metric_name}={val_str})"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _safe_divide(numerator: float, denominator: float) -> Optional[float]:
    """
    Safely divide two numbers, returning None for division by zero or None values.

    Args:
        numerator: The dividend
        denominator: The divisor

    Returns:
        The quotient, or None if denominator is zero or numerator is None
    """
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _calculate_cagr(
    start_value: float,
    end_value: float,
    years: int
) -> Optional[float]:
    """
    Calculate Compound Annual Growth Rate (CAGR).

    Formula: CAGR = (End Value / Start Value)^(1/years) - 1

    Args:
        start_value: Initial value
        end_value: Final value
        years: Number of years between measurements

    Returns:
        CAGR as a decimal (e.g., 0.15 for 15%), or None if invalid
    """
    if years <= 0:
        return None
    if start_value is None or start_value == 0:
        return None
    if end_value is None or end_value <= 0 or start_value <= 0:
        return None

    try:
        cagr = (end_value / start_value) ** (1 / years) - 1
        return cagr
    except (ValueError, ZeroDivisionError):
        return None


def _ensure_positive(value: float, name: str = "value") -> Optional[float]:
    """
    Ensure a value is positive for ratio calculations.

    Some financial ratios require positive denominators.
    Returns None if the value is not positive.
    """
    if value is None or value <= 0:
        return None
    return value


# =============================================================================
# GROWTH METRICS
# =============================================================================

def revenue_cagr(
    revenue_start: float,
    revenue_end: float,
    years: int
) -> MetricResult:
    """
    Calculate Revenue CAGR.

    Formula: CAGR = (Revenue_end / Revenue_start)^(1/years) - 1

    Args:
        revenue_start: Revenue at the start of the period
        revenue_end: Revenue at the end of the period
        years: Number of years between measurements

    Returns:
        MetricResult with CAGR value (as decimal)
    """
    value = _calculate_cagr(revenue_start, revenue_end, years)
    return MetricResult(
        value=value,
        metric_name="revenue_cagr",
        formula=f"(Revenue_end / Revenue_start)^(1/{years}) - 1",
        notes="Returns decimal (multiply by 100 for percentage)"
    )


def earnings_cagr(
    earnings_start: float,
    earnings_end: float,
    years: int
) -> MetricResult:
    """
    Calculate Earnings (Net Income) CAGR.

    Formula: CAGR = (Net Income_end / Net Income_start)^(1/years) - 1

    Args:
        earnings_start: Net income at the start
        earnings_end: Net income at the end
        years: Number of years

    Returns:
        MetricResult with CAGR value
    """
    value = _calculate_cagr(earnings_start, earnings_end, years)
    return MetricResult(
        value=value,
        metric_name="earnings_cagr",
        formula=f"(Net Income_end / Net Income_start)^(1/{years}) - 1"
    )


def eps_cagr(
    eps_start: float,
    eps_end: float,
    years: int
) -> MetricResult:
    """
    Calculate EPS CAGR.

    Formula: CAGR = (EPS_end / EPS_start)^(1/years) - 1

    Args:
        eps_start: EPS at the start
        eps_end: EPS at the end
        years: Number of years

    Returns:
        MetricResult with CAGR value
    """
    value = _calculate_cagr(eps_start, eps_end, years)
    return MetricResult(
        value=value,
        metric_name="eps_cagr",
        formula=f"(EPS_end / EPS_start)^(1/{years}) - 1"
    )


def fcf_cagr(
    fcf_start: float,
    fcf_end: float,
    years: int
) -> MetricResult:
    """
    Calculate Free Cash Flow CAGR.

    Formula: CAGR = (FCF_end / FCF_start)^(1/years) - 1

    Args:
        fcf_start: Free cash flow at the start
        fcf_end: Free cash flow at the end
        years: Number of years

    Returns:
        MetricResult with CAGR value
    """
    value = _calculate_cagr(fcf_start, fcf_end, years)
    return MetricResult(
        value=value,
        metric_name="fcf_cagr",
        formula=f"(FCF_end / FCF_start)^(1/{years}) - 1"
    )


# =============================================================================
# PROFITABILITY METRICS
# =============================================================================

def gross_margin(gross_profit: float, revenue: float) -> MetricResult:
    """
    Calculate Gross Margin.

    Formula: Gross Margin = Gross Profit / Revenue

    Args:
        gross_profit: Gross profit in currency units
        revenue: Total revenue in same currency units

    Returns:
        MetricResult with margin as decimal (e.g., 0.45 for 45%)
    """
    revenue_pos = _ensure_positive(revenue, "revenue")
    if gross_profit is None or revenue_pos is None:
        return MetricResult(
            value=None,
            metric_name="gross_margin",
            formula="Gross Profit / Revenue"
        )

    value = gross_profit / revenue_pos
    return MetricResult(
        value=value,
        metric_name="gross_margin",
        formula="Gross Profit / Revenue",
        notes="Returns decimal (multiply by 100 for percentage)"
    )


def operating_margin(operating_income: float, revenue: float) -> MetricResult:
    """
    Calculate Operating Margin.

    Formula: Operating Margin = Operating Income / Revenue

    Args:
        operating_income: Operating income (EBIT)
        revenue: Total revenue

    Returns:
        MetricResult with margin as decimal
    """
    revenue_pos = _ensure_positive(revenue, "revenue")
    if operating_income is None or revenue_pos is None:
        return MetricResult(
            value=None,
            metric_name="operating_margin",
            formula="Operating Income / Revenue"
        )

    value = operating_income / revenue_pos
    return MetricResult(
        value=value,
        metric_name="operating_margin",
        formula="Operating Income / Revenue"
    )


def net_margin(net_income: float, revenue: float) -> MetricResult:
    """
    Calculate Net Profit Margin.

    Formula: Net Margin = Net Income / Revenue

    Args:
        net_income: Net income (profit after tax)
        revenue: Total revenue

    Returns:
        MetricResult with margin as decimal
    """
    revenue_pos = _ensure_positive(revenue, "revenue")
    if net_income is None or revenue_pos is None:
        return MetricResult(
            value=None,
            metric_name="net_margin",
            formula="Net Income / Revenue"
        )

    value = net_income / revenue_pos
    return MetricResult(
        value=value,
        metric_name="net_margin",
        formula="Net Income / Revenue"
    )


def roe(net_income: float, total_equity: float) -> MetricResult:
    """
    Calculate Return on Equity (ROE).

    Formula: ROE = Net Income / Average Shareholders' Equity

    Note: For single-period calculation, we use ending equity.
    For more accuracy, average of beginning and ending equity should be used.

    Args:
        net_income: Net income for the period
        total_equity: Total shareholders' equity

    Returns:
        MetricResult with ROE as decimal
    """
    equity_pos = _ensure_positive(total_equity, "total_equity")
    if net_income is None or equity_pos is None:
        return MetricResult(
            value=None,
            metric_name="roe",
            formula="Net Income / Total Equity"
        )

    value = net_income / equity_pos
    return MetricResult(
        value=value,
        metric_name="roe",
        formula="Net Income / Total Equity",
        notes="Returns decimal (multiply by 100 for percentage)"
    )


def roa(net_income: float, total_assets: float) -> MetricResult:
    """
    Calculate Return on Assets (ROA).

    Formula: ROA = Net Income / Total Assets

    Args:
        net_income: Net income for the period
        total_assets: Total assets

    Returns:
        MetricResult with ROA as decimal
    """
    assets_pos = _ensure_positive(total_assets, "total_assets")
    if net_income is None or assets_pos is None:
        return MetricResult(
            value=None,
            metric_name="roa",
            formula="Net Income / Total Assets"
        )

    value = net_income / assets_pos
    return MetricResult(
        value=value,
        metric_name="roa",
        formula="Net Income / Total Assets"
    )


def roic(
    net_income: float,
    total_equity: float,
    total_debt: float,
    tax_rate: Optional[float] = None
) -> MetricResult:
    """
    Calculate Return on Invested Capital (ROIC).

    Formula: ROIC = NOPAT / Invested Capital
              where NOPAT = EBIT * (1 - Tax Rate)
              and Invested Capital = Total Equity + Total Debt - Cash

    Simplified: ROIC = Net Income / (Total Equity + Total Debt)

    Args:
        net_income: Net income
        total_equity: Total shareholders' equity
        total_debt: Total debt
        tax_rate: Optional effective tax rate (0-1). If None, uses net income directly.

    Returns:
        MetricResult with ROIC as decimal
    """
    # Check for None values first
    if net_income is None or total_equity is None or total_debt is None:
        return MetricResult(
            value=None,
            metric_name="roic",
            formula="Net Income / (Total Equity + Total Debt)"
        )

    # Return None if equity is negative (financial distress signal)
    if total_equity < 0:
        return MetricResult(
            value=None,
            metric_name="roic",
            formula="Net Income / (Total Equity + Total Debt)",
            notes="Negative equity indicates financial distress"
        )

    capital = total_equity + total_debt

    # Return None if capital is not positive
    if capital <= 0:
        return MetricResult(
            value=None,
            metric_name="roic",
            formula="Net Income / (Total Equity + Total Debt)",
            notes="Invested capital must be positive"
        )

    if tax_rate is not None and 0 < tax_rate < 1:
        # Use NOPAT approach
        # Note: We need EBIT, but using net income as proxy when EBIT unavailable
        value = net_income / capital
    else:
        value = net_income / capital

    return MetricResult(
        value=value,
        metric_name="roic",
        formula="Net Income / Invested Capital",
        notes="Simplified ROIC; use EBIT*(1-tax) for precise calculation"
    )


# =============================================================================
# FINANCIAL HEALTH METRICS
# =============================================================================

def debt_to_equity(total_debt: float, total_equity: float) -> MetricResult:
    """
    Calculate Debt-to-Equity Ratio.

    Formula: D/E = Total Debt / Total Equity

    Args:
        total_debt: Total debt (short-term + long-term)
        total_equity: Total shareholders' equity

    Returns:
        MetricResult with ratio (e.g., 0.5 means 50% debt relative to equity)
    """
    equity_pos = _ensure_positive(total_equity, "total_equity")
    if total_debt is None or equity_pos is None:
        return MetricResult(
            value=None,
            metric_name="debt_to_equity",
            formula="Total Debt / Total Equity"
        )

    value = total_debt / equity_pos
    return MetricResult(
        value=value,
        metric_name="debt_to_equity",
        formula="Total Debt / Total Equity"
    )


def net_debt_to_ebitda(
    total_debt: float,
    cash: float,
    ebitda: float
) -> MetricResult:
    """
    Calculate Net Debt to EBITDA Ratio.

    Formula: Net Debt / EBITDA
              where Net Debt = Total Debt - Cash & Equivalents

    Args:
        total_debt: Total debt
        cash: Cash and cash equivalents
        ebitda: Earnings Before Interest, Taxes, Depreciation, and Amortization

    Returns:
        MetricResult with ratio (lower is better for debt sustainability)
    """
    net_debt = total_debt - cash if total_debt is not None and cash is not None else None
    ebitda_pos = _ensure_positive(ebitda, "ebitda")

    if net_debt is None or ebitda_pos is None:
        return MetricResult(
            value=None,
            metric_name="net_debt_to_ebitda",
            formula="(Total Debt - Cash) / EBITDA"
        )

    value = net_debt / ebitda_pos
    return MetricResult(
        value=value,
        metric_name="net_debt_to_ebitda",
        formula="(Total Debt - Cash) / EBITDA"
    )


def current_ratio(current_assets: float, current_liabilities: float) -> MetricResult:
    """
    Calculate Current Ratio.

    Formula: Current Ratio = Current Assets / Current Liabilities

    Args:
        current_assets: Total current assets
        current_liabilities: Total current liabilities

    Returns:
        MetricResult with ratio (>1 indicates good short-term liquidity)
    """
    liabilities_pos = _ensure_positive(current_liabilities, "current_liabilities")
    if current_assets is None or liabilities_pos is None:
        return MetricResult(
            value=None,
            metric_name="current_ratio",
            formula="Current Assets / Current Liabilities"
        )

    value = current_assets / liabilities_pos
    return MetricResult(
        value=value,
        metric_name="current_ratio",
        formula="Current Assets / Current Liabilities"
    )


def interest_coverage(ebit: float, interest_expense: float) -> MetricResult:
    """
    Calculate Interest Coverage Ratio.

    Formula: Interest Coverage = EBIT / Interest Expense

    Also known as Times Interest Earned (TIE).

    Args:
        ebit: Earnings Before Interest and Taxes
        interest_expense: Interest expense for the period

    Returns:
        MetricResult with ratio (>1.5 generally considered safe)
    """
    interest_pos = _ensure_positive(interest_expense, "interest_expense")
    if ebit is None or interest_pos is None:
        return MetricResult(
            value=None,
            metric_name="interest_coverage",
            formula="EBIT / Interest Expense"
        )

    value = ebit / interest_pos
    return MetricResult(
        value=value,
        metric_name="interest_coverage",
        formula="EBIT / Interest Expense"
    )


# =============================================================================
# CASH FLOW METRICS
# =============================================================================

def free_cash_flow(
    operating_cash_flow: float,
    capital_expenditures: float
) -> MetricResult:
    """
    Calculate Free Cash Flow (FCF).

    Formula: FCF = Operating Cash Flow - Capital Expenditures

    Args:
        operating_cash_flow: Cash from operating activities
        capital_expenditures: CapEx (typically positive number representing outflow)

    Returns:
        MetricResult with FCF value (positive = cash generated, negative = cash consumed)
    """
    if operating_cash_flow is None or capital_expenditures is None:
        return MetricResult(
            value=None,
            metric_name="free_cash_flow",
            formula="Operating Cash Flow - Capital Expenditures"
        )

    value = operating_cash_flow - capital_expenditures
    return MetricResult(
        value=value,
        metric_name="free_cash_flow",
        formula="Operating Cash Flow - Capital Expenditures"
    )


def fcf_margin(free_cash_flow: float, revenue: float) -> MetricResult:
    """
    Calculate Free Cash Flow Margin.

    Formula: FCF Margin = Free Cash Flow / Revenue

    Args:
        free_cash_flow: Free cash flow
        revenue: Total revenue

    Returns:
        MetricResult with margin as decimal
    """
    revenue_pos = _ensure_positive(revenue, "revenue")
    if free_cash_flow is None or revenue_pos is None:
        return MetricResult(
            value=None,
            metric_name="fcf_margin",
            formula="Free Cash Flow / Revenue"
        )

    value = free_cash_flow / revenue_pos
    return MetricResult(
        value=value,
        metric_name="fcf_margin",
        formula="Free Cash Flow / Revenue"
    )


# =============================================================================
# BATCH CALCULATION FROM FinancialMetrics
# =============================================================================

def _stored_cagr(value, metric_name: str) -> MetricResult:
    """Wrap a precomputed CAGR value from the data source into a MetricResult.

    ``FinancialMetrics`` can carry revenue/earnings/EPS CAGR that was already
    computed during ingestion (e.g. ``compute_cagr`` backfill). Without this the
    growth section reported "not available" even though the number is stored.
    """
    if value is None:
        return MetricResult(
            value=None,
            metric_name=metric_name,
            formula="CAGR stored in data source",
        )
    return MetricResult(
        value=float(value),
        metric_name=metric_name,
        formula="CAGR stored in data source",
        notes="Returns decimal (multiply by 100 for percentage)",
    )


def calculate_all_metrics(metrics: FinancialMetrics, period_label: str = "") -> dict:
    """
    Calculate all fundamental metrics from a FinancialMetrics object.

    This is the main entry point for fundamental analysis. It computes all
    available ratios and growth rates from the provided metrics.

    Args:
        metrics: FinancialMetrics object with period data
        period_label: Human-readable period label (e.g., "2024")

    Returns:
        Dictionary mapping metric names to MetricResult objects
    """
    results = {}

    # Profitability metrics
    results["gross_margin"] = gross_margin(metrics.gross_profit, metrics.revenue)
    results["operating_margin"] = operating_margin(metrics.operating_income, metrics.revenue)
    results["net_margin"] = net_margin(metrics.net_income, metrics.revenue)
    results["roe"] = roe(metrics.net_income, metrics.total_equity)
    results["roa"] = roa(metrics.net_income, metrics.total_assets)
    results["roic"] = roic(
        metrics.net_income,
        metrics.total_equity,
        metrics.total_debt
    )

    # Financial health metrics
    results["debt_to_equity"] = debt_to_equity(metrics.total_debt, metrics.total_equity)
    results["net_debt_to_ebitda"] = net_debt_to_ebitda(
        metrics.total_debt,
        metrics.cash_and_equivalents,
        metrics.operating_income  # Using OI as proxy for EBITDA when unavailable
    )
    # Prefer a precomputed current ratio from the data source (e.g. the DB row
    # stores ``current_ratio`` directly without the assets/liabilities split).
    if metrics.current_ratio is not None:
        results["current_ratio"] = MetricResult(
            value=float(metrics.current_ratio),
            metric_name="current_ratio",
            formula="(from data source)",
        )
    else:
        results["current_ratio"] = current_ratio(
            metrics.current_assets,
            metrics.current_liabilities
        )
    results["interest_coverage"] = interest_coverage(
        metrics.operating_income,  # Using OI as proxy for EBIT
        metrics.interest_expense
    )

    # Growth metrics (CAGR) — use stored values when available, otherwise the
    # components are not present and the metric stays unavailable.
    results["revenue_cagr_3y"] = _stored_cagr(metrics.revenue_cagr_3y, "revenue_cagr_3y")
    results["earnings_cagr_3y"] = _stored_cagr(metrics.earnings_cagr_3y, "earnings_cagr_3y")
    results["eps_cagr_3y"] = _stored_cagr(metrics.eps_cagr_3y, "eps_cagr_3y")

    # Cash flow metrics
    results["free_cash_flow"] = free_cash_flow(
        metrics.operating_cash_flow,
        metrics.capital_expenditures
    )
    results["fcf_margin"] = fcf_margin(
        results["free_cash_flow"].value if results["free_cash_flow"].is_available else None,
        metrics.revenue
    )

    # Add period info
    for result in results.values():
        if result.period is None:
            result.period = period_label

    return results


def calculate_growth_metrics(
    previous_metrics: FinancialMetrics,
    current_metrics: FinancialMetrics,
    years_apart: int = 1
) -> dict:
    """
    Calculate growth metrics by comparing two periods.

    Args:
        previous_metrics: FinancialMetrics from earlier period
        current_metrics: FinancialMetrics from current period
        years_apart: Number of years between periods

    Returns:
        Dictionary of growth MetricResults
    """
    results = {}

    results["revenue_cagr"] = revenue_cagr(
        previous_metrics.revenue,
        current_metrics.revenue,
        years_apart
    )
    results["earnings_cagr"] = earnings_cagr(
        previous_metrics.net_income,
        current_metrics.net_income,
        years_apart
    )
    results["eps_cagr"] = eps_cagr(
        previous_metrics.eps,
        current_metrics.eps,
        years_apart
    )
    results["fcf_cagr"] = fcf_cagr(
        previous_metrics.free_cash_flow,
        current_metrics.free_cash_flow,
        years_apart
    )

    return results


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_latest_ratios(metrics: FinancialMetrics) -> dict:
    """
    Extract already-calculated ratios from FinancialMetrics if available.

    This is useful when the data source already provides computed ratios
    (like IDX API which provides ROE, P/E, etc.).

    Args:
        metrics: FinancialMetrics object

    Returns:
        Dictionary of pre-calculated ratios
    """
    ratios = {}

    if metrics.roe is not None:
        ratios["roe"] = metrics.roe
    if metrics.roa is not None:
        ratios["roa"] = metrics.roa
    if metrics.debt_to_equity is not None:
        ratios["debt_to_equity"] = metrics.debt_to_equity
    if metrics.pe_ratio is not None:
        ratios["pe_ratio"] = metrics.pe_ratio
    if metrics.pb_ratio is not None:
        ratios["pb_ratio"] = metrics.pb_ratio
    if metrics.net_margin is not None:
        ratios["net_margin"] = metrics.net_margin
    if metrics.gross_margin is not None:
        ratios["gross_margin"] = metrics.gross_margin
    if metrics.operating_margin is not None:
        ratios["operating_margin"] = metrics.operating_margin

    return ratios
