"""
Performance Metrics for Backtesting.

This module provides deterministic calculations for evaluating backtest results.
All metrics are calculated without lookahead bias.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class MetricResult:
    """
    Result of a performance metric calculation.

    Contains the calculated value along with metadata about the calculation.
    """
    value: Optional[float]
    metric_name: str
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    notes: str = ""

    @property
    def is_available(self) -> bool:
        """Check if the metric has a valid calculated value."""
        return self.value is not None

    def __repr__(self) -> str:
        val_str = f"{self.value:.4f}" if self.value is not None else "N/A"
        return f"MetricResult({self.metric_name}={val_str})"


def calculate_cagr(
    start_value: float,
    end_value: float,
    years: int
) -> MetricResult:
    """
    Calculate Compound Annual Growth Rate (CAGR).

    Formula: CAGR = (End Value / Start Value)^(1/years) - 1

    Args:
        start_value: Initial portfolio value
        end_value: Final portfolio value
        years: Number of years in the backtest period

    Returns:
        MetricResult with CAGR value
    """
    if years <= 0:
        return MetricResult(
            value=None,
            metric_name="cagr",
            notes="Invalid period length"
        )

    if start_value <= 0 or end_value <= 0:
        return MetricResult(
            value=None,
            metric_name="cagr",
            notes="Invalid portfolio values"
        )

    try:
        cagr = (end_value / start_value) ** (1 / years) - 1
        return MetricResult(
            value=cagr,
            metric_name="cagr",
            notes="Compound Annual Growth Rate"
        )
    except (ValueError, ZeroDivisionError):
        return MetricResult(
            value=None,
            metric_name="cagr",
            notes="Calculation error"
        )


def calculate_volatility(
    returns: List[float],
    annualize: bool = True
) -> MetricResult:
    """
    Calculate portfolio volatility (standard deviation of returns).

    Args:
        returns: List of periodic returns (e.g., daily returns)
        annualize: Whether to annualize the volatility

    Returns:
        MetricResult with volatility value
    """
    if len(returns) < 2:
        return MetricResult(
            value=None,
            metric_name="volatility",
            notes="Insufficient data for volatility calculation"
        )

    try:
        std_dev = np.std(returns, ddof=1)  # Sample standard deviation

        if annualize:
            # Assume daily returns, annualize by sqrt(252)
            annualized = std_dev * np.sqrt(252)
            return MetricResult(
                value=annualized,
                metric_name="volatility",
                notes="Annualized standard deviation of returns"
            )

        return MetricResult(
            value=std_dev,
            metric_name="volatility",
            notes="Standard deviation of returns"
        )
    except Exception:
        return MetricResult(
            value=None,
            metric_name="volatility",
            notes="Calculation error"
        )


def calculate_sharpe_ratio(
    returns: List[float],
    risk_free_rate: float = 0.06,
    periods_per_year: int = 252
) -> MetricResult:
    """
    Calculate Sharpe ratio.

    Formula: Sharpe Ratio = (Portfolio Return - Risk-Free Rate) / Portfolio Volatility

    Args:
        returns: List of periodic returns
        risk_free_rate: Annual risk-free rate (default 6% for Indonesia)
        periods_per_year: Number of periods per year (default 252 for daily)

    Returns:
        MetricResult with Sharpe ratio
    """
    if len(returns) < 2:
        return MetricResult(
            value=None,
            metric_name="sharpe_ratio",
            notes="Insufficient data for Sharpe ratio"
        )

    try:
        avg_return = np.mean(returns)
        std_dev = np.std(returns, ddof=1)

        if std_dev == 0:
            return MetricResult(
                value=None,
                metric_name="sharpe_ratio",
                notes="Zero volatility prevents Sharpe calculation"
            )

        # Annualize the risk-free rate to match the return period
        periodic_risk_free = risk_free_rate / periods_per_year

        sharpe = (avg_return - periodic_risk_free) / std_dev
        # Annualize Sharpe ratio
        annualized_sharpe = sharpe * np.sqrt(periods_per_year)

        return MetricResult(
            value=annualized_sharpe,
            metric_name="sharpe_ratio",
            notes=f"Sharpe ratio (risk-free rate: {risk_free_rate:.2%})"
        )
    except Exception:
        return MetricResult(
            value=None,
            metric_name="sharpe_ratio",
            notes="Calculation error"
        )


def calculate_max_drawdown(
    equity_curve: List[float]
) -> MetricResult:
    """
    Calculate maximum drawdown from an equity curve.

    Maximum Drawdown = Max((Peak - Trough) / Peak)

    Args:
        equity_curve: List of portfolio values over time

    Returns:
        MetricResult with max drawdown (negative value)
    """
    if len(equity_curve) < 2:
        return MetricResult(
            value=None,
            metric_name="max_drawdown",
            notes="Insufficient data for drawdown calculation"
        )

    try:
        peak = equity_curve[0]
        max_dd = 0.0

        for value in equity_curve:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_dd:
                max_dd = drawdown

        # Return as positive number representing the magnitude of loss
        return MetricResult(
            value=max_dd,
            metric_name="max_drawdown",
            notes="Maximum peak-to-trough decline"
        )
    except Exception:
        return MetricResult(
            value=None,
            metric_name="max_drawdown",
            notes="Calculation error"
        )


def calculate_win_rate(
    trades: List[Dict]
) -> MetricResult:
    """
    Calculate win rate from a list of trades.

    Win Rate = Winning Trades / Total Trades

    Args:
        trades: List of trade dictionaries with 'profit' key

    Returns:
        MetricResult with win rate (0.0 to 1.0)
    """
    if not trades:
        return MetricResult(
            value=None,
            metric_name="win_rate",
            notes="No trades to analyze"
        )

    winning_trades = sum(1 for trade in trades if trade.get("profit", 0) > 0)
    win_rate = winning_trades / len(trades)

    return MetricResult(
        value=win_rate,
        metric_name="win_rate",
        notes=f"{winning_trades} wins out of {len(trades)} trades"
    )


def calculate_turnover(
    trades: List[Dict]
) -> MetricResult:
    """
    Calculate portfolio turnover rate.

    Turnover = Total Buy/Sell Volume / Average Portfolio Value

    Args:
        trades: List of trade dictionaries

    Returns:
        MetricResult with turnover rate
    """
    if not trades:
        return MetricResult(
            value=None,
            metric_name="turnover",
            notes="No trades to analyze"
        )

    total_volume = sum(abs(trade.get("value", 0)) for trade in trades)

    # For simplicity, assume average portfolio value is the final value
    # In practice, this would need historical portfolio values
    if len(trades) > 0:
        avg_value = trades[-1].get("portfolio_value", total_volume)
        if avg_value > 0:
            turnover = total_volume / avg_value
        else:
            turnover = None
    else:
        turnover = None

    return MetricResult(
        value=turnover,
        metric_name="turnover",
        notes="Ratio of trading volume to portfolio value"
    )


def calculate_total_return(
    initial_value: float,
    final_value: float
) -> MetricResult:
    """
    Calculate total return over the backtest period.

    Args:
        initial_value: Portfolio value at start
        final_value: Portfolio value at end

    Returns:
        MetricResult with total return
    """
    if initial_value <= 0:
        return MetricResult(
            value=None,
            metric_name="total_return",
            notes="Invalid initial value"
        )

    total_return = (final_value - initial_value) / initial_value

    return MetricResult(
        value=total_return,
        metric_name="total_return",
        notes="Total percentage return over period"
    )


def calculate_benchmark_comparison(
    strategy_returns: List[float],
    benchmark_returns: List[float],
) -> MetricResult:
    """
    Calculate active return (strategy return minus benchmark return).

    Args:
        strategy_returns: List of strategy periodic returns
        benchmark_returns: List of benchmark periodic returns

    Returns:
        MetricResult with active return
    """
    if len(strategy_returns) != len(benchmark_returns):
        return MetricResult(
            value=None,
            metric_name="active_return",
            notes="Return series must be same length"
        )

    if len(strategy_returns) < 2:
        return MetricResult(
            value=None,
            metric_name="active_return",
            notes="Insufficient data"
        )

    try:
        strategy_cumulative = (1 + np.mean(strategy_returns)) ** len(strategy_returns) - 1
        benchmark_cumulative = (1 + np.mean(benchmark_returns)) ** len(benchmark_returns) - 1
        active_return = strategy_cumulative - benchmark_cumulative

        return MetricResult(
            value=active_return,
            metric_name="active_return",
            notes="Strategy return minus benchmark return"
        )
    except Exception:
        return MetricResult(
            value=None,
            metric_name="active_return",
            notes="Calculation error"
        )
