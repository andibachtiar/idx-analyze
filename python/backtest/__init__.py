"""
Backtesting Engine for idx-bei.

This module provides deterministic backtesting capabilities for investment strategies.
All calculations are purely mathematical — no AI/LLM involvement.

Features:
- Strategy interface for defining investable criteria
- Look-ahead bias prevention (uses only data available at decision date)
- Performance metrics: CAGR, volatility, Sharpe ratio, max drawdown, win rate
- Multiple strategy implementations (Value, Growth, Quality, Technical)

Example:
    from backtest import BacktestEngine, ValueStrategy

    engine = BacktestEngine(
        ticker="BBCA.JK",
        start_date="2020-01-01",
        end_date="2024-12-31"
    )

    strategy = ValueStrategy(pe_max=20, pb_max=2)
    result = engine.run(strategy)

    print(f"Annual Return: {result.annual_return:.2%}")
    print(f"Max Drawdown: {result.max_drawdown:.2%}")
"""

from .engine import BacktestEngine, BacktestResult
from .metrics import (
    calculate_cagr,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    calculate_turnover,
    calculate_volatility,
    calculate_win_rate,
)
from .strategies import (
    GrowthStrategy,
    QualityStrategy,
    Strategy,
    TechnicalStrategy,
    ValueStrategy,
)

__all__ = [
    "BacktestEngine",
    "BacktestResult",
    "calculate_cagr",
    "calculate_volatility",
    "calculate_sharpe_ratio",
    "calculate_max_drawdown",
    "calculate_win_rate",
    "calculate_turnover",
    "Strategy",
    "ValueStrategy",
    "GrowthStrategy",
    "QualityStrategy",
    "TechnicalStrategy",
]
