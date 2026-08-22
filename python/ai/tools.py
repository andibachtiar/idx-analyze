"""
AI Tool Functions for idx-bei investment research platform.

This module provides structured tool functions that the AI analyst can use
to retrieve stock data and analysis results.

Tools return structured dictionaries suitable for AI consumption:
- Clear field names
- Consistent formats
- Missing data indicated as None
- All calculations are deterministic (from existing engines)
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

from analysis.fundamental import (
    calculate_all_metrics,
    current_ratio,
    debt_to_equity,
    earnings_cagr,
    eps_cagr,
    fcf_margin,
    gross_margin,
    interest_coverage,
    net_debt_to_ebitda,
    net_margin,
    operating_margin,
    revenue_cagr,
    roa,
    roe,
    roic,
)
from analysis.historical import (
    analyze_company_growth,
    get_financial_trends,
)
from analysis.screening import (
    ScreenFilter,
    ScreenOperator,
    create_buffett_screen,
    create_dividend_screen,
    create_growth_screen,
    create_quality_screen,
    create_technical_screen,
    create_value_screen,
    screen_stocks,
)
from analysis.technical import (
    TechnicalResult,
    get_technical_summary,
)
from analysis.valuation import (
    ValuationResult,
    calculate_all_valuations,
    get_valuation_summary,
)
from backtest.engine import BacktestEngine
from backtest.strategies import ValueStrategy
from models import FinancialMetrics

# =============================================================================
# TOOL RESULT HELPERS
# =============================================================================

def _safe_float(value: Any) -> Optional[float]:
    """Convert a value to float safely, returning None for invalid values."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _format_metric_result(result: Any) -> Dict[str, Any]:
    """Format a MetricResult or similar object into a dict."""
    if result is None:
        return {"value": None, "is_available": False}

    if hasattr(result, 'value'):
        return {
            "value": result.value,
            "is_available": result.is_available if hasattr(result, 'is_available') else result.value is not None,
            "metric_name": getattr(result, 'metric_name', None),
            "notes": getattr(result, 'notes', ''),
        }

    # If it's already a dict, return as-is
    if isinstance(result, dict):
        return result

    return {"value": result, "is_available": True}


def _format_structured_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure all values in a result dict are JSON-serializable."""
    result = {}
    for key, value in data.items():
        if isinstance(value, (date, datetime)):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = _format_structured_result(value)
        elif isinstance(value, list):
            formatted_list = []
            for item in value:
                if isinstance(item, dict):
                    formatted_list.append(_format_structured_result(item))
                elif isinstance(item, (date, datetime)):
                    formatted_list.append(item.isoformat())
                else:
                    formatted_list.append(item)
            result[key] = formatted_list
        else:
            result[key] = value
    return result


# =============================================================================
# CORE TOOLS
# =============================================================================

def get_stock_price(ticker: str, source: str = "yfinance") -> Dict[str, Any]:
    """
    Get current/recent stock price for a ticker.

    Args:
        ticker: Stock ticker symbol (e.g., "BBCA")
        source: Data source ("yfinance" or "idx")

    Returns:
        Dictionary with price information
    """
    return {
        "ticker": ticker.upper(),
        "price": None,
        "currency": "IDR",
        "source": source,
        "as_of": str(date.today()),
        "notes": "Price data not yet implemented - requires market data integration"
    }


def get_financials(
    ticker: str,
    period: str = "latest",
    period_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get normalized financial metrics for a ticker.

    Args:
        ticker: Stock ticker symbol
        period: Period identifier ("latest", "annual", "quarterly", or specific date)
        period_type: Override period type ("annual" or "quarterly")

    Returns:
        Dictionary with financial metrics
    """
    return {
        "ticker": ticker.upper(),
        "period": period,
        "period_type": period_type,
        "metrics": None,
        "source": "database",
        "as_of": str(date.today()),
        "notes": "Financial data not yet implemented - requires database integration"
    }


def get_fundamental_analysis(ticker: str, metrics: Optional[FinancialMetrics] = None) -> Dict[str, Any]:
    """
    Get comprehensive fundamental analysis for a ticker.

    Args:
        ticker: Stock ticker symbol
        metrics: Optional FinancialMetrics object (if available)

    Returns:
        Dictionary with fundamental analysis results
    """
    result = {
        "ticker": ticker.upper(),
        "calculated_at": str(datetime.now()),
        "growth": {},
        "profitability": {},
        "financial_health": {},
        "cash_flow": {},
    }

    if metrics is None:
        result["notes"] = "No financial metrics provided - cannot calculate fundamentals"
        return result

    # Validate metrics type
    if not isinstance(metrics, FinancialMetrics):
        result["notes"] = f"Invalid metrics type: {type(metrics).__name__}. Expected FinancialMetrics."
        return result

    # Use calculate_all_metrics for comprehensive analysis
    try:
        all_metrics = calculate_all_metrics(metrics)
    except AttributeError as e:
        result["notes"] = f"Error calculating metrics: {e}"
        return result

    # Growth metrics
    result["growth"] = {
        "revenue_cagr_3y": _format_metric_result(all_metrics.get("revenue_cagr_3y")),
        "earnings_cagr_3y": _format_metric_result(all_metrics.get("earnings_cagr_3y")),
        "eps_cagr_3y": _format_metric_result(all_metrics.get("eps_cagr_3y")),
    }

    # Profitability metrics
    result["profitability"] = {
        "gross_margin": _format_metric_result(all_metrics.get("gross_margin")),
        "operating_margin": _format_metric_result(all_metrics.get("operating_margin")),
        "net_margin": _format_metric_result(all_metrics.get("net_margin")),
        "roe": _format_metric_result(all_metrics.get("roe")),
        "roa": _format_metric_result(all_metrics.get("roa")),
        "roic": _format_metric_result(all_metrics.get("roic")),
    }

    # Financial health metrics
    result["financial_health"] = {
        "debt_to_equity": _format_metric_result(all_metrics.get("debt_to_equity")),
        "net_debt_to_ebitda": _format_metric_result(all_metrics.get("net_debt_to_ebitda")),
        "current_ratio": _format_metric_result(all_metrics.get("current_ratio")),
        "interest_coverage": _format_metric_result(all_metrics.get("interest_coverage")),
    }

    # Cash flow metrics
    result["cash_flow"] = {
        "fcf_margin": _format_metric_result(all_metrics.get("fcf_margin")),
    }

    return _format_structured_result(result)


def get_technical_analysis(
    ticker: str,
    prices: Optional[List[float]] = None,
    volumes: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Get technical analysis for a ticker.

    Args:
        ticker: Stock ticker symbol
        prices: Optional list of closing prices (most recent last)
        volumes: Optional list of trading volumes

    Returns:
        Dictionary with technical analysis results
    """
    result = {
        "ticker": ticker.upper(),
        "calculated_at": str(datetime.now()),
        "indicators": {},
        "signals": {},
    }

    if prices is None or len(prices) < 20:
        result["notes"] = "Insufficient price data for technical analysis"
        return result

    # Get technical summary
    summary = get_technical_summary(prices)

    result["indicators"] = summary.get("indicators", {})

    # Generate signals based on indicators
    signals = {}

    # Trend signal
    sma_200 = result["indicators"].get("sma_200", {})
    current_price = prices[-1] if prices else None
    if sma_200.get("value") and current_price:
        if current_price > sma_200["value"]:
            signals["trend"] = "bullish"
        elif current_price < sma_200["value"]:
            signals["trend"] = "bearish"
        else:
            signals["trend"] = "neutral"

    # RSI signal
    rsi_14 = result["indicators"].get("rsi_14", {})
    if rsi_14.get("value"):
        rsi_val = rsi_14["value"]
        if rsi_val > 70:
            signals["rsi"] = "overbought"
        elif rsi_val < 30:
            signals["rsi"] = "oversold"
        else:
            signals["rsi"] = "neutral"

    # MACD signal
    macd = result["indicators"].get("macd", {})
    if macd.get("value"):
        signals["macd"] = "bullish" if macd["value"] > 0 else "bearish"

    result["signals"] = signals

    return _format_structured_result(result)


def get_valuation(
    ticker: str,
    price: Optional[float] = None,
    metrics: Optional[FinancialMetrics] = None,
    historical_pe: Optional[List[tuple]] = None,
    historical_pb: Optional[List[tuple]] = None
) -> Dict[str, Any]:
    """
    Get valuation analysis for a ticker.

    Args:
        ticker: Stock ticker symbol
        price: Current stock price
        metrics: FinancialMetrics object
        historical_pe: Optional historical P/E ratios for comparison
        historical_pb: Optional historical P/B ratios for comparison

    Returns:
        Dictionary with valuation results
    """
    if price is None or metrics is None:
        return {
            "ticker": ticker.upper(),
            "valuations": {},
            "notes": "Price and financial metrics required for valuation"
        }

    # Convert tuples to lists for JSON serialization
    hist_pe = [(d, v) for d, v in historical_pe] if historical_pe else None
    hist_pb = [(d, v) for d, v in historical_pb] if historical_pb else None

    summary = get_valuation_summary(
        price=price,
        metrics=metrics,
        historical_pe=hist_pe,
        historical_pb=hist_pb,
        valuation_date=date.today()
    )

    # Add ticker to summary
    summary["ticker"] = ticker.upper()

    return _format_structured_result(summary)


def get_historical_analysis(
    ticker: str,
    raw_data: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Get historical financial analysis for a ticker.

    Args:
        ticker: Stock ticker symbol
        raw_data: Optional list of raw financial data dictionaries

    Returns:
        Dictionary with historical analysis (growth rates, trends)
    """
    result = {
        "ticker": ticker.upper(),
        "calculated_at": str(datetime.now()),
        "growth": {},
        "trends": {},
    }

    if raw_data is None or len(raw_data) < 2:
        result["notes"] = "Insufficient historical data for analysis"
        return result

    # Analyze growth
    growth_results = analyze_company_growth(ticker, raw_data)
    result["growth"] = {
        metric: _format_metric_result(res)
        for metric, res in growth_results.items()
    }

    # Analyze trends
    trends = get_financial_trends(ticker, raw_data)
    result["trends"] = trends

    return _format_structured_result(result)


def get_company_news(
    ticker: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get recent news for a company.

    Args:
        ticker: Stock ticker symbol
        limit: Maximum number of news articles to return

    Returns:
        Dictionary with news articles
    """
    return {
        "ticker": ticker.upper(),
        "news": [],
        "count": 0,
        "limit": limit,
        "notes": "News integration not yet implemented"
    }


def get_ownership(ticker: str) -> Dict[str, Any]:
    """
    Get ownership and relationship data for a company.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dictionary with ownership information
    """
    return {
        "ticker": ticker.upper(),
        "insiders": [],
        "major_shareholders": [],
        "related_companies": [],
        "notes": "Neo4j integration not yet implemented"
    }


def run_screening(
    filters: Optional[List[Dict]] = None,
    screen_type: Optional[str] = None,
    stocks: Optional[Dict[str, Dict]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Run stock screening with specified criteria.

    Args:
        filters: Optional list of filter dictionaries
        screen_type: Predefined screen type ("buffett", "growth", "value", etc.)
        stocks: Optional dictionary of stocks to screen
        **kwargs: Additional parameters for the screen

    Returns:
        Dictionary with screening results
    """
    if stocks is None:
        return {
            "results": [],
            "count": 0,
            "notes": "No stocks provided for screening"
        }

    # Create filters from screen_type if provided
    if screen_type and not filters:
        # Map screen types to creator functions
        screen_creators = {
            "buffett": create_buffett_screen,
            "growth": create_growth_screen,
            "value": create_value_screen,
            "quality": create_quality_screen,
            "technical": create_technical_screen,
            "dividend": create_dividend_screen,
        }
        creator = screen_creators.get(screen_type.lower())
        if not creator:
            return {
                "results": [],
                "count": 0,
                "notes": f"Unknown screen type: {screen_type}"
            }
        filters_obj = creator(**kwargs)
    elif filters:
        # Validate filters is a list
        if not isinstance(filters, list):
            return {
                "results": [],
                "count": 0,
                "notes": "Filters must be a list of dictionaries"
            }
        # Convert dict filters to ScreenFilter objects
        filters_obj = []
        for f in filters:
            if isinstance(f, dict):
                # Convert operator string to enum
                op_str = f.get("operator", ">=")
                op_map = {
                    ">": ScreenOperator.GREATER_THAN,
                    "<": ScreenOperator.LESS_THAN,
                    ">=": ScreenOperator.GREATER_EQUAL,
                    "<=": ScreenOperator.LESS_EQUAL,
                    "=": ScreenOperator.EQUAL,
                    "between": ScreenOperator.BETWEEN,
                    "range": ScreenOperator.IN_RANGE,
                }
                operator = op_map.get(op_str, ScreenOperator.GREATER_EQUAL)
                filters_obj.append(
                    ScreenFilter(
                        metric=f.get("metric", ""),
                        operator=operator,
                        value=f.get("value", 0),
                        description=f.get("description", "")
                    )
                )
            else:
                return {
                    "results": [],
                    "count": 0,
                    "notes": "Each filter must be a dictionary"
                }
    else:
        return {
            "results": [],
            "count": 0,
            "notes": "No filters or screen type provided"
        }

    # Run screening
    result = screen_stocks(stocks, filters_obj, min_pass_rate=0)

    # Format results
    formatted_results = []
    for stock_result in result.results:
        formatted_results.append({
            "ticker": stock_result.ticker,
            "passed": stock_result.passed,
            "score": stock_result.score,
            "pass_rate": stock_result.pass_rate,
            "filter_results": {
                metric: {"passed": passed, "reason": reason}
                for metric, (passed, reason) in stock_result.filters.items()
            }
        })

    return {
        "results": formatted_results,
        "count": len(formatted_results),
        "stocks_passed": result.stocks_passed,
        "total_screened": result.total_stocks_screened,
    }


def compare_stocks(tickers: List[str]) -> Dict[str, Any]:
    """
    Compare multiple stocks side-by-side.

    Args:
        tickers: List of ticker symbols to compare

    Returns:
        Dictionary with comparison data
    """
    comparison = {
        "tickers": [t.upper() for t in tickers],
        "comparison_date": str(date.today()),
        "stocks": {}
    }

    for ticker in tickers:
        comparison["stocks"][ticker.upper()] = {
            "fundamentals": "Not available - requires data integration",
            "valuation": "Not available - requires data integration",
            "technical": "Not available - requires data integration",
        }

    return comparison


def run_backtest(
    ticker: str,
    strategy: str = "value",
    start_date: str = "2023-01-01",
    end_date: str = "2023-12-31",
    initial_capital: float = 100000000,
    rebalance_frequency: str = "monthly",
    **strategy_params
) -> Dict[str, Any]:
    """
    Run a backtest simulation for a stock.

    Args:
        ticker: Stock ticker symbol
        strategy: Strategy type ("value", "growth", "quality", "technical")
        start_date: Backtest start date
        end_date: Backtest end date
        initial_capital: Starting portfolio value
        rebalance_frequency: How often to rebalance
        **strategy_params: Additional strategy parameters

    Returns:
        Dictionary with backtest results
    """
    # Create engine
    engine = BacktestEngine(
        ticker=ticker.upper(),
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
    )

    # TODO: Add price data to engine

    # Create strategy
    from backtest.strategies import (
        GrowthStrategy,
        QualityStrategy,
        TechnicalStrategy,
        ValueStrategy,
    )

    strategies = {
        "value": ValueStrategy(**strategy_params),
        "growth": GrowthStrategy(**strategy_params),
        "quality": QualityStrategy(**strategy_params),
        "technical": TechnicalStrategy(**strategy_params),
    }

    selected_strategy = strategies.get(strategy, ValueStrategy(**strategy_params))

    # Run backtest
    # Note: This will fail without price data
    try:
        result = engine.run(selected_strategy, rebalance_frequency)
        return {
            "ticker": result.ticker,
            "strategy": result.strategy_name,
            "period": f"{result.start_date.date()} to {result.end_date.date()}",
            "initial_capital": result.initial_capital,
            "final_value": result.final_value,
            "total_return": result.total_return,
            "annual_return": result.annual_return,
            "volatility": result.volatility,
            "sharpe_ratio": result.sharpe_ratio,
            "max_drawdown": result.max_drawdown,
            "win_rate": result.win_rate,
            "total_trades": result.total_trades,
            "notes": result.notes,
        }
    except Exception as e:
        return {
            "ticker": ticker.upper(),
            "error": str(e),
            "notes": "Backtest requires price data integration"
        }


# =============================================================================
# BATCH TOOLS
# =============================================================================

def get_stock_profile(ticker: str) -> Dict[str, Any]:
    """
    Get comprehensive profile for a stock including all analysis types.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dictionary with complete stock profile
    """
    return {
        "ticker": ticker.upper(),
        "profile": "Not available - requires data integration",
        "fundamentals": "Not available - requires data integration",
        "valuation": "Not available - requires data integration",
        "technical": "Not available - requires data integration",
        "historical": "Not available - requires data integration",
        "news": "Not available - requires data integration",
        "ownership": "Not available - requires data integration",
    }


def batch_screen(stocks: List[str], screen_type: str = "buffett") -> Dict[str, Any]:
    """
    Screen a list of stocks with a predefined screen type.

    Args:
        stocks: List of ticker symbols
        screen_type: Type of screen to apply

    Returns:
        Dictionary with screening results
    """
    # Create stock data dictionary (empty for now - would need data source)
    stock_data = {s.upper(): {} for s in stocks}

    return run_screening(stocks=stock_data, screen_type=screen_type)


def batch_compare(tickers: List[str]) -> Dict[str, Any]:
    """
    Compare multiple stocks side-by-side.

    Args:
        tickers: List of ticker symbols

    Returns:
        Dictionary with comparison results
    """
    return compare_stocks(tickers)
