"""
Analysis module for idx-bei investment research platform.

Provides deterministic financial analysis functions for:
- Fundamental analysis
- Historical financial analysis
- Technical analysis
- Valuation analysis
"""

from analysis.fundamental import (
    # MetricResult class
    MetricResult,
    _calculate_cagr,
    _ensure_positive,
    # Helper functions
    _safe_divide,
    # Batch calculations
    calculate_all_metrics,
    calculate_growth_metrics,
    current_ratio,
    # Financial health metrics
    debt_to_equity,
    earnings_cagr,
    eps_cagr,
    fcf_cagr,
    fcf_margin,
    # Cash flow metrics
    free_cash_flow,
    get_latest_ratios,
    # Profitability metrics
    gross_margin,
    interest_coverage,
    net_debt_to_ebitda,
    net_margin,
    operating_margin,
    # Growth metrics
    revenue_cagr,
    roa,
    roe,
    roic,
)
from analysis.historical import (
    GrowthResult,
    HistoricalFinancialData,
    # Core classes
    HistoricalRecord,
    analyze_company_growth,
    # Convenience functions
    create_historical_data,
    get_financial_trends,
)
from analysis.technical import (
    # Core classes
    TechnicalResult,
    # Volatility
    atr,
    # Bollinger Bands
    bollinger_bands,
    # Batch functions
    calculate_all_technicals,
    drawdown,
    ema,
    # Support/Resistance
    find_support_resistance,
    get_technical_summary,
    macd,
    # Price Position
    price_vs_sma,
    # Momentum
    rsi,
    # Moving Averages
    sma,
    volatility,
    volume_ratio,
    # Volume
    volume_sma,
)
from analysis.valuation import (
    HistoricalValuation,
    # Core classes
    ValuationResult,
    add_historical_context,
    # Batch operations
    calculate_all_valuations,
    calculate_dividend_yield,
    calculate_ev_ebit,
    calculate_ev_ebitda,
    # Historical analysis
    calculate_historical_percentile,
    calculate_pb_ratio,
    calculate_pe_fcf,
    # Valuation metrics
    calculate_pe_ratio,
    get_valuation_signal,
    get_valuation_summary,
)

__all__ = [
    # Fundamental Analysis
    "MetricResult",
    "revenue_cagr",
    "earnings_cagr",
    "eps_cagr",
    "fcf_cagr",
    "gross_margin",
    "operating_margin",
    "net_margin",
    "roe",
    "roa",
    "roic",
    "debt_to_equity",
    "net_debt_to_ebitda",
    "current_ratio",
    "interest_coverage",
    "free_cash_flow",
    "fcf_margin",
    "calculate_all_metrics",
    "calculate_growth_metrics",
    "get_latest_ratios",

    # Historical Analysis
    "HistoricalRecord",
    "GrowthResult",
    "HistoricalFinancialData",
    "create_historical_data",
    "analyze_company_growth",
    "get_financial_trends",

    # Technical Analysis
    "TechnicalResult",
    "sma",
    "ema",
    "rsi",
    "macd",
    "atr",
    "volatility",
    "drawdown",
    "volume_sma",
    "volume_ratio",
    "bollinger_bands",
    "find_support_resistance",
    "price_vs_sma",
    "calculate_all_technicals",
    "get_technical_summary",

    # Valuation Analysis
    "ValuationResult",
    "HistoricalValuation",
    "calculate_pe_ratio",
    "calculate_pb_ratio",
    "calculate_ev_ebitda",
    "calculate_ev_ebit",
    "calculate_pe_fcf",
    "calculate_dividend_yield",
    "calculate_historical_percentile",
    "add_historical_context",
    "calculate_all_valuations",
    "get_valuation_summary",
    "get_valuation_signal",
]
