"""
Valuation Engine for idx-bei.

This module provides deterministic valuation calculations for Indonesian stocks.
All calculations are purely mathematical — no AI/LLM involvement.

Valuation metrics implemented:
- P/E (Price-to-Earnings) ratio
- P/B (Price-to-Book) ratio
- EV/EBITDA (Enterprise Value to EBITDA)
- EV/EBIT (Enterprise Value to EBIT)
- P/FCF (Price-to-Free Cash Flow)
- Dividend Yield
- Historical valuation percentiles (5-year median comparison)

Each valuation result contains:
- Input values
- Formula/model used
- Calculated output
- Valuation date
- Data source
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple

from models import FinancialMetrics, FinancialPeriod


@dataclass
class ValuationResult:
    """
    Result of a valuation calculation.

    Contains the calculated value along with metadata about the calculation.
    """
    value: Optional[float]
    metric_name: str
    formula: str
    inputs: Dict[str, float]
    valuation_date: Optional[date] = None
    data_source: str = "manual"
    notes: str = ""

    @property
    def is_available(self) -> bool:
        """Check if the valuation has a valid calculated value."""
        return self.value is not None

    def __repr__(self) -> str:
        val_str = f"{self.value:.4f}" if self.value is not None else "N/A"
        return f"ValuationResult({self.metric_name}={val_str})"


@dataclass
class HistoricalValuation:
    """
    Historical valuation comparison.

    Compares current valuation to historical percentiles.
    """
    current_value: Optional[float]
    metric_name: str
    period_label: str
    history: List[Tuple[str, float]]  # List of (period, value)
    percentile: Optional[float] = None  # Current percentile in historical range
    median_5y: Optional[float] = None
    mean_5y: Optional[float] = None
    std_dev_5y: Optional[float] = None

    @property
    def is_available(self) -> bool:
        return self.current_value is not None

    @property
    def is_expensive(self) -> bool:
        """Current valuation is above 75th percentile."""
        return self.percentile is not None and self.percentile > 75

    @property
    def is_cheap(self) -> bool:
        """Current valuation is below 25th percentile."""
        return self.percentile is not None and self.percentile < 25

    def __repr__(self) -> str:
        val_str = f"{self.current_value:.4f}" if self.current_value else "N/A"
        return f"HistoricalValuation({self.metric_name}={val_str}, pctl={self.percentile})"


# =============================================================================
# CORE VALUATION FUNCTIONS
# =============================================================================

def calculate_pe_ratio(
    price: float,
    eps: float,
    valuation_date: Optional[date] = None,
    data_source: str = "manual"
) -> ValuationResult:
    """
    Calculate Price-to-Earnings (P/E) ratio.

    Formula: P/E = Price per Share / Earnings per Share

    Args:
        price: Current stock price
        eps: Earnings per share (annual)
        valuation_date: Date of valuation
        data_source: Source of data

    Returns:
        ValuationResult with P/E ratio
    """
    if eps is None or eps == 0:
        return ValuationResult(
            value=None,
            metric_name="pe_ratio",
            formula="Price / EPS",
            inputs={"price": price, "eps": eps},
            valuation_date=valuation_date,
            data_source=data_source,
            notes="EPS is zero or missing"
        )

    pe = price / eps

    return ValuationResult(
        value=pe,
        metric_name="pe_ratio",
        formula="Price / EPS",
        inputs={"price": price, "eps": eps},
        valuation_date=valuation_date,
        data_source=data_source
    )


def calculate_pb_ratio(
    price: float,
    book_value_per_share: float,
    valuation_date: Optional[date] = None,
    data_source: str = "manual"
) -> ValuationResult:
    """
    Calculate Price-to-Book (P/B) ratio.

    Formula: P/B = Price per Share / Book Value per Share

    Args:
        price: Current stock price
        book_value_per_share: Book value per share
        valuation_date: Date of valuation
        data_source: Source of data

    Returns:
        ValuationResult with P/B ratio
    """
    if book_value_per_share is None or book_value_per_share == 0:
        return ValuationResult(
            value=None,
            metric_name="pb_ratio",
            formula="Price / Book Value per Share",
            inputs={"price": price, "bvps": book_value_per_share},
            valuation_date=valuation_date,
            data_source=data_source,
            notes="Book value per share is zero or missing"
        )

    pb = price / book_value_per_share

    return ValuationResult(
        value=pb,
        metric_name="pb_ratio",
        formula="Price / Book Value per Share",
        inputs={"price": price, "bvps": book_value_per_share},
        valuation_date=valuation_date,
        data_source=data_source
    )


def calculate_ev_ebitda(
    market_cap: float,
    total_debt: float,
    cash: float,
    ebitda: float,
    valuation_date: Optional[date] = None,
    data_source: str = "manual"
) -> ValuationResult:
    """
    Calculate Enterprise Value to EBITDA ratio.

    Formula: EV/EBITDA = (Market Cap + Total Debt - Cash) / EBITDA

    Args:
        market_cap: Market capitalization
        total_debt: Total debt
        cash: Cash and cash equivalents
        ebitda: Earnings Before Interest, Taxes, Depreciation, and Amortization
        valuation_date: Date of valuation
        data_source: Source of data

    Returns:
        ValuationResult with EV/EBITDA ratio
    """
    ev = market_cap + total_debt - cash

    if ebitda is None or ebitda == 0:
        return ValuationResult(
            value=None,
            metric_name="ev_ebitda",
            formula="(Market Cap + Debt - Cash) / EBITDA",
            inputs={"market_cap": market_cap, "debt": total_debt,
                    "cash": cash, "ebitda": ebitda},
            valuation_date=valuation_date,
            data_source=data_source,
            notes="EBITDA is zero or missing"
        )

    ev_ebitda = ev / ebitda

    return ValuationResult(
        value=ev_ebitda,
        metric_name="ev_ebitda",
        formula="(Market Cap + Debt - Cash) / EBITDA",
        inputs={"enterprise_value": ev, "ebitda": ebitda},
        valuation_date=valuation_date,
        data_source=data_source
    )


def calculate_ev_ebit(
    market_cap: float,
    total_debt: float,
    cash: float,
    ebit: float,
    valuation_date: Optional[date] = None,
    data_source: str = "manual"
) -> ValuationResult:
    """
    Calculate Enterprise Value to EBIT ratio.

    Formula: EV/EBIT = (Market Cap + Total Debt - Cash) / EBIT

    Args:
        market_cap: Market capitalization
        total_debt: Total debt
        cash: Cash and cash equivalents
        ebit: Earnings Before Interest and Taxes
        valuation_date: Date of valuation
        data_source: Source of data

    Returns:
        ValuationResult with EV/EBIT ratio
    """
    ev = market_cap + total_debt - cash

    if ebit is None or ebit == 0:
        return ValuationResult(
            value=None,
            metric_name="ev_ebit",
            formula="(Market Cap + Debt - Cash) / EBIT",
            inputs={"market_cap": market_cap, "debt": total_debt,
                    "cash": cash, "ebit": ebit},
            valuation_date=valuation_date,
            data_source=data_source,
            notes="EBIT is zero or missing"
        )

    ev_ebit = ev / ebit

    return ValuationResult(
        value=ev_ebit,
        metric_name="ev_ebit",
        formula="(Market Cap + Debt - Cash) / EBIT",
        inputs={"enterprise_value": ev, "ebit": ebit},
        valuation_date=valuation_date,
        data_source=data_source
    )


def calculate_pe_fcf(
    price: float,
    free_cash_flow_per_share: float,
    valuation_date: Optional[date] = None,
    data_source: str = "manual"
) -> ValuationResult:
    """
    Calculate Price-to-Free Cash Flow ratio.

    Formula: P/FCF = Price per Share / Free Cash Flow per Share

    Args:
        price: Current stock price
        free_cash_flow_per_share: FCF per share
        valuation_date: Date of valuation
        data_source: Source of data

    Returns:
        ValuationResult with P/FCF ratio
    """
    if free_cash_flow_per_share is None or free_cash_flow_per_share <= 0:
        return ValuationResult(
            value=None,
            metric_name="pe_fcf",
            formula="Price / Free Cash Flow per Share",
            inputs={"price": price, "fcf_per_share": free_cash_flow_per_share},
            valuation_date=valuation_date,
            data_source=data_source,
            notes="FCF per share is zero, negative, or missing"
        )

    pe_fcf = price / free_cash_flow_per_share

    return ValuationResult(
        value=pe_fcf,
        metric_name="pe_fcf",
        formula="Price / Free Cash Flow per Share",
        inputs={"price": price, "fcf_per_share": free_cash_flow_per_share},
        valuation_date=valuation_date,
        data_source=data_source
    )


def calculate_dividend_yield(
    annual_dividend_per_share: float,
    price: float,
    valuation_date: Optional[date] = None,
    data_source: str = "manual"
) -> ValuationResult:
    """
    Calculate Dividend Yield.

    Formula: Dividend Yield = (Annual Dividend per Share / Price) * 100

    Args:
        annual_dividend_per_share: Annual dividend per share
        price: Current stock price
        valuation_date: Date of valuation
        data_source: Source of data

    Returns:
        ValuationResult with dividend yield (as percentage)
    """
    if price is None or price == 0:
        return ValuationResult(
            value=None,
            metric_name="dividend_yield",
            formula="(Annual Dividend / Price) * 100",
            inputs={"dividend_per_share": annual_dividend_per_share, "price": price},
            valuation_date=valuation_date,
            data_source=data_source,
            notes="Price is zero or missing"
        )

    yield_pct = (annual_dividend_per_share / price) * 100

    return ValuationResult(
        value=yield_pct,
        metric_name="dividend_yield",
        formula="(Annual Dividend / Price) * 100",
        inputs={"dividend_per_share": annual_dividend_per_share, "price": price},
        valuation_date=valuation_date,
        data_source=data_source
    )


# =============================================================================
# HISTORICAL VALUATION ANALYSIS
# =============================================================================

def calculate_historical_percentile(
    current_value: float,
    historical_values: List[float]
) -> Optional[float]:
    """
    Calculate the percentile rank of a value within historical data.

    Args:
        current_value: The current value to rank
        historical_values: List of historical values

    Returns:
        Percentile rank (0-100), or None if insufficient data
    """
    if len(historical_values) < 2:
        return None

    sorted_values = sorted(historical_values)
    count_below = sum(1 for v in sorted_values if v < current_value)
    percentile = (count_below / len(sorted_values)) * 100

    return percentile


def add_historical_context(
    valuation: ValuationResult,
    historical_values: List[Tuple[str, float]]
) -> HistoricalValuation:
    """
    Add historical context to a valuation result.

    Calculates percentile, median, and mean over the historical period.

    Args:
        valuation: The current valuation result
        historical_values: List of (period_label, value) tuples

    Returns:
        HistoricalValuation with additional context
    """
    if not historical_values or valuation.value is None:
        return HistoricalValuation(
            current_value=valuation.value,
            metric_name=valuation.metric_name,
            period_label=valuation.valuation_date.isoformat() if valuation.valuation_date else "unknown",
            history=[]
        )

    values = [v for _, v in historical_values if v is not None and v > 0]

    if not values:
        return HistoricalValuation(
            current_value=valuation.value,
            metric_name=valuation.metric_name,
            period_label=valuation.valuation_date.isoformat() if valuation.valuation_date else "unknown",
            history=historical_values
        )

    percentile = calculate_historical_percentile(valuation.value, values)
    median = sorted(values)[len(values) // 2] if values else None
    mean = sum(values) / len(values) if values else None
    std_dev = (sum((x - mean) ** 2 for x in values) / len(values)) ** 0.5 if values and mean else None

    return HistoricalValuation(
        current_value=valuation.value,
        metric_name=valuation.metric_name,
        period_label=valuation.valuation_date.isoformat() if valuation.valuation_date else "unknown",
        history=historical_values,
        percentile=percentile,
        median_5y=median,
        mean_5y=mean,
        std_dev_5y=std_dev
    )


# =============================================================================
# BATCH VALUATION CALCULATION
# =============================================================================

def calculate_all_valuations(
    price: float,
    metrics: FinancialMetrics,
    market_cap: Optional[float] = None,
    total_debt: Optional[float] = None,
    cash: Optional[float] = None,
    annual_dividend: Optional[float] = None,
    valuation_date: Optional[date] = None,
    data_source: str = "manual"
) -> Dict[str, ValuationResult]:
    """
    Calculate all available valuation metrics.

    Args:
        price: Current stock price
        metrics: FinancialMetrics object with required financial data
        market_cap: Optional market capitalization (for EV calculations)
        total_debt: Optional total debt (for EV calculations)
        cash: Optional cash position (for EV calculations)
        annual_dividend: Optional annual dividend per share
        valuation_date: Date of valuation
        data_source: Source of data

    Returns:
        Dictionary mapping metric names to ValuationResult objects
    """
    results = {}

    # P/E Ratio
    results["pe_ratio"] = calculate_pe_ratio(
        price, metrics.eps, valuation_date, data_source
    )

    # P/B Ratio
    bvps = metrics.book_value_per_share or (
        metrics.total_equity / metrics.shares_outstanding
        if metrics.total_equity and metrics.shares_outstanding
        else None
    )
    results["pb_ratio"] = calculate_pb_ratio(
        price, bvps, valuation_date, data_source
    )

    # EV/EBITDA (if data available)
    if market_cap is not None and metrics.operating_income is not None:
        # Use operating income as proxy for EBITDA when EBITDA not available
        ev = market_cap + (total_debt or 0) - (cash or 0)
        ebitda_proxy = metrics.operating_income  # Simplified
        results["ev_ebitda"] = ValuationResult(
            value=ev / ebitda_proxy if ebitda_proxy > 0 else None,
            metric_name="ev_ebitda",
            formula="(Market Cap + Debt - Cash) / EBITDA",
            inputs={"enterprise_value": ev, "ebitda": ebitda_proxy},
            valuation_date=valuation_date,
            data_source=data_source
        )

    # P/FCF (if FCF available)
    if metrics.free_cash_flow and metrics.shares_outstanding:
        fcf_per_share = metrics.free_cash_flow / metrics.shares_outstanding
        results["pe_fcf"] = calculate_pe_fcf(
            price, fcf_per_share, valuation_date, data_source
        )

    # Dividend Yield
    if annual_dividend is not None:
        results["dividend_yield"] = calculate_dividend_yield(
            annual_dividend, price, valuation_date, data_source
        )

    return results


def get_valuation_summary(
    price: float,
    metrics: FinancialMetrics,
    historical_pe: Optional[List[Tuple[str, float]]] = None,
    historical_pb: Optional[List[Tuple[str, float]]] = None,
    valuation_date: Optional[date] = None,
    data_source: str = "manual"
) -> Dict[str, any]:
    """
    Get a comprehensive valuation summary with historical context.

    Args:
        price: Current stock price
        metrics: FinancialMetrics object
        historical_pe: Optional list of (period, pe_ratio) for historical comparison
        historical_pb: Optional list of (period, pb_ratio) for historical comparison
        valuation_date: Date of valuation
        data_source: Source of data

    Returns:
        Dictionary with complete valuation summary
    """
    # Calculate current valuations
    valuations = calculate_all_valuations(
        price=price,
        metrics=metrics,
        valuation_date=valuation_date,
        data_source=data_source
    )

    # Add historical context
    summary = {
        "ticker": "UNKNOWN",  # Would be set by caller
        "valuation_date": valuation_date.isoformat() if valuation_date else str(date.today()),
        "current_price": price,
        "valuations": {},
        "historical_comparison": {}
    }

    # Process each valuation
    if "pe_ratio" in valuations and valuations["pe_ratio"].is_available:
        summary["valuations"]["pe_ratio"] = {
            "value": valuations["pe_ratio"].value,
            "formula": valuations["pe_ratio"].formula,
            "inputs": valuations["pe_ratio"].inputs
        }

        if historical_pe:
            hist = add_historical_context(
                valuations["pe_ratio"], historical_pe
            )
            summary["historical_comparison"]["pe_ratio"] = {
                "current": hist.current_value,
                "median_5y": hist.median_5y,
                "percentile": hist.percentile,
                "is_expensive": hist.is_expensive,
                "is_cheap": hist.is_cheap
            }

    if "pb_ratio" in valuations and valuations["pb_ratio"].is_available:
        summary["valuations"]["pb_ratio"] = {
            "value": valuations["pb_ratio"].value,
            "formula": valuations["pb_ratio"].formula,
            "inputs": valuations["pb_ratio"].inputs
        }

        if historical_pb:
            hist = add_historical_context(
                valuations["pb_ratio"], historical_pb
            )
            summary["historical_comparison"]["pb_ratio"] = {
                "current": hist.current_value,
                "median_5y": hist.median_5y,
                "percentile": hist.percentile,
                "is_expensive": hist.is_expensive,
                "is_cheap": hist.is_cheap
            }

    return summary


# =============================================================================
# VALUATION SIGNALS
# =============================================================================

def get_valuation_signal(
    pe_result: Optional[ValuationResult],
    pb_result: Optional[ValuationResult],
    pe_hist_percentile: Optional[float] = None,
    pb_hist_percentile: Optional[float] = None
) -> str:
    """
    Determine overall valuation signal based on multiple indicators.

    Signal logic:
    - "Cheap": Both P/E and P/B below 25th percentile, or below industry averages
    - "Expensive": Both P/E and P/B above 75th percentile, or above industry averages
    - "Fair": Mixed signals
    - "Insufficient Data": Not enough information to determine

    Args:
        pe_result: P/E valuation result
        pb_result: P/B valuation result
        pe_hist_percentile: Historical percentile for P/E
        pb_hist_percentile: Historical percentile for P/B

    Returns:
        Signal string: "cheap", "expensive", "fair", or "insufficient_data"
    """
    signals = []

    # Check P/E signal
    if pe_result and pe_result.is_available:
        if pe_hist_percentile is not None:
            if pe_hist_percentile < 25:
                signals.append("pe_cheap")
            elif pe_hist_percentile > 75:
                signals.append("pe_expensive")
            else:
                signals.append("pe_fair")
        else:
            # Use absolute thresholds as fallback
            if pe_result.value < 15:
                signals.append("pe_cheap")
            elif pe_result.value > 25:
                signals.append("pe_expensive")
            else:
                signals.append("pe_fair")

    # Check P/B signal
    if pb_result and pb_result.is_available:
        if pb_hist_percentile is not None:
            if pb_hist_percentile < 25:
                signals.append("pb_cheap")
            elif pb_hist_percentile > 75:
                signals.append("pb_expensive")
            else:
                signals.append("pb_fair")
        else:
            if pb_result.value < 1.5:
                signals.append("pb_cheap")
            elif pb_result.value > 3.0:
                signals.append("pb_expensive")
            else:
                signals.append("pb_fair")

    # Determine overall signal
    if not signals:
        return "insufficient_data"

    cheap_count = sum(1 for s in signals if "cheap" in s)
    expensive_count = sum(1 for s in signals if "expensive" in s)
    fair_count = sum(1 for s in signals if "fair" in s)

    if cheap_count >= 2:
        return "cheap"
    elif expensive_count >= 2:
        return "expensive"
    elif cheap_count > expensive_count:
        return "fair_to_cheap"
    elif expensive_count > cheap_count:
        return "fair_to_expensive"
    else:
        return "fair"
