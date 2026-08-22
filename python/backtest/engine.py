"""
Backtesting Engine for idx-bei.

This module provides the core backtesting engine that simulates
investment strategies against historical data while preventing
look-ahead bias.

Key principles:
- Strategies can only use data available at decision date
- All calculations are deterministic
- Results include full trade history and performance metrics
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .metrics import (
    MetricResult,
    calculate_benchmark_comparison,
    calculate_cagr,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    calculate_total_return,
    calculate_turnover,
    calculate_volatility,
    calculate_win_rate,
)
from .strategies import Signal, Strategy, StrategyType


@dataclass
class BacktestResult:
    """
    Complete results from a backtest simulation.

    Attributes:
        ticker: Stock ticker symbol
        strategy_name: Name of the strategy used
        strategy_type: Type of strategy
        start_date: Beginning of backtest period
        end_date: End of backtest period
        initial_capital: Starting portfolio value
        final_value: Ending portfolio value
        total_return: Total percentage return
        annual_return: Annualized return (CAGR)
        volatility: Annualized volatility
        sharpe_ratio: Risk-adjusted return measure
        max_drawdown: Largest peak-to-trough decline
        win_rate: Percentage of winning trades
        total_trades: Number of trades executed
        turnover: Portfolio turnover rate
        trades: List of individual trades
        benchmark_return: Benchmark performance (if provided)
        notes: Additional information
    """
    ticker: str
    strategy_name: str
    strategy_type: StrategyType
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_value: float
    total_return: Optional[float] = None
    annual_return: Optional[float] = None
    volatility: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    total_trades: int = 0
    turnover: Optional[float] = None
    trades: List[Dict] = field(default_factory=list)
    benchmark_return: Optional[float] = None
    benchmark_trades: List[Dict] = field(default_factory=list)
    notes: str = ""

    @property
    def is_successful(self) -> bool:
        """Check if backtest completed successfully."""
        return self.final_value > 0 and self.total_trades >= 0

    def get_summary(self) -> Dict[str, Any]:
        """Get summary dictionary of results."""
        return {
            "ticker": self.ticker,
            "strategy": self.strategy_name,
            "period": f"{self.start_date.date()} to {self.end_date.date()}",
            "initial_value": self.initial_capital,
            "final_value": self.final_value,
            "total_return": self.total_return,
            "annual_return": self.annual_return,
            "volatility": self.volatility,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "benchmark_return": self.benchmark_return,
        }

    def __repr__(self) -> str:
        return_val = f"{self.total_return:.2%}" if self.total_return is not None else 'N/A'
        return (
            f"BacktestResult({self.ticker}, {self.strategy_name}, "
            f"return={return_val}, "
            f"trades={self.total_trades})"
        )


class BacktestEngine:
    """
    Core backtesting engine.

    Simulates investment strategies against historical price and
    financial data while preventing look-ahead bias.

    Example:
        engine = BacktestEngine(
            ticker="BBCA.JK",
            start_date="2020-01-01",
            end_date="2024-12-31"
        )
        result = engine.run(ValueStrategy())
    """

    def __init__(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 1000000.0,
        benchmark_ticker: Optional[str] = None,
    ):
        """
        Initialize the backtest engine.

        Args:
            ticker: Stock ticker symbol (e.g., "BBCA.JK")
            start_date: Backtest start date (YYYY-MM-DD)
            end_date: Backtest end date (YYYY-MM-DD)
            initial_capital: Starting portfolio value in IDR
            benchmark_ticker: Optional benchmark ticker for comparison
        """
        self.ticker = ticker.upper()
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.initial_capital = initial_capital
        self.benchmark_ticker = benchmark_ticker

        # Internal state
        self._price_data: List[Dict] = []
        self._financial_data: Dict[str, List[Dict]] = {}
        self._benchmark_data: List[Dict] = []

    def add_price_data(self, data: List[Dict]) -> None:
        """
        Add historical price data.

        Each record should contain at minimum:
        - date: datetime or string date
        - close: closing price

        Args:
            data: List of price records
        """
        self._price_data = sorted(data, key=lambda x: x.get("date", x.get("Date")))

    def add_financial_data(
        self,
        data: List[Dict],
        metric_name: str = "default"
    ) -> None:
        """
        Add historical financial data.

        Financial data is indexed by date and used to provide
        context for strategy decisions without look-ahead bias.

        Args:
            data: List of financial data records
            metric_name: Name to identify this dataset
        """
        self._financial_data[metric_name] = sorted(
            data,
            key=lambda x: x.get("date", x.get("Date"))
        )

    def add_benchmark_data(self, data: List[Dict]) -> None:
        """
        Add benchmark price data for comparison.

        Args:
            data: List of benchmark price records
        """
        self._benchmark_data = sorted(
            data,
            key=lambda x: x.get("date", x.get("Date"))
        )

    def run(
        self,
        strategy: Strategy,
        rebalance_frequency: str = "monthly"
    ) -> BacktestResult:
        """
        Run the backtest simulation.

        Simulates the strategy over the historical period, generating
        trades and calculating performance metrics.

        Args:
            strategy: Strategy instance to test
            rebalance_frequency: How often to check for trades
                ('daily', 'weekly', 'monthly')

        Returns:
            BacktestResult with complete simulation results
        """
        # Initialize portfolio state
        cash = self.initial_capital
        shares = 0
        trades = []
        equity_curve = [self.initial_capital]
        strategy_type = strategy.get_type()

        # Get rebalance dates
        rebalance_dates = self._get_rebalance_dates(rebalance_frequency)

        # Track available financial data (for look-ahead prevention)
        available_financials: Dict[str, Any] = {}

        # Get financial data cutoff dates
        financial_dates = self._get_financial_dates()

        for date in rebalance_dates:
            if date > self.end_date:
                break

            # Update available financial data (no look-ahead!)
            available_financials = self._get_available_financials(date, financial_dates)

            # Get current price
            price_record = self._get_price_at_date(date)
            if price_record is None:
                continue

            current_price = price_record.get("close", 0)
            if current_price <= 0:
                continue

            # Generate trading signal
            signal = strategy.generate_signal(date, current_price, available_financials)

            # Execute trade if signal is not HOLD
            if signal != Signal.HOLD:
                trade_value = self._calculate_trade_value(
                    cash, shares, current_price, signal
                )

                if trade_value > 0:
                    if signal == Signal.BUY and cash > 0:
                        # Buy shares
                        qty = int(trade_value / current_price)
                        if qty > 0:
                            cost = qty * current_price
                            cash -= cost
                            shares += qty
                            trades.append({
                                "date": date.isoformat(),
                                "action": "buy",
                                "ticker": self.ticker,
                                "quantity": qty,
                                "price": current_price,
                                "value": cost,
                                "reason": strategy.get_name(),
                                "portfolio_value": self._get_portfolio_value(
                                    cash, shares, current_price
                                ),
                            })

                    elif signal == Signal.SELL and shares > 0:
                        # Sell shares
                        revenue = shares * current_price
                        cash += revenue
                        trades.append({
                            "date": date.isoformat(),
                            "action": "sell",
                            "ticker": self.ticker,
                            "quantity": shares,
                            "price": current_price,
                            "value": revenue,
                            "reason": strategy.get_name(),
                            "portfolio_value": cash,
                        })
                        shares = 0

            # Record portfolio value
            portfolio_value = self._get_portfolio_value(
                cash, shares, current_price
            )
            equity_curve.append(portfolio_value)

        # Calculate final portfolio value
        final_price_record = self._get_price_at_date(self.end_date)
        final_price = final_price_record.get("close", 0) if final_price_record else 0

        if final_price > 0 and shares > 0:
            final_value = cash + (shares * final_price)
        else:
            final_value = cash

        # Calculate performance metrics
        metrics = self._calculate_metrics(
            equity_curve, trades, self.initial_capital, final_value
        )

        # Run benchmark if available
        benchmark_result = None
        if self.benchmark_ticker and self._benchmark_data:
            benchmark_result = self._run_benchmark()

        return BacktestResult(
            ticker=self.ticker,
            strategy_name=strategy.get_name(),
            strategy_type=strategy_type,
            start_date=self.start_date,
            end_date=self.end_date,
            initial_capital=self.initial_capital,
            final_value=final_value,
            total_return=metrics["total_return"].value if metrics["total_return"] else None,
            annual_return=metrics["annual_return"].value if metrics["annual_return"] else None,
            volatility=metrics["volatility"].value if metrics["volatility"] else None,
            sharpe_ratio=metrics["sharpe_ratio"].value if metrics["sharpe_ratio"] else None,
            max_drawdown=metrics["max_drawdown"].value if metrics["max_drawdown"] else None,
            win_rate=metrics["win_rate"].value if metrics["win_rate"] else None,
            total_trades=len(trades),
            turnover=metrics["turnover"].value if metrics["turnover"] else None,
            trades=trades,
            benchmark_return=benchmark_result.get("total_return") if benchmark_result else None,
            benchmark_trades=benchmark_result.get("trades", []) if benchmark_result else [],
            notes=metrics.get("notes", ""),
        )

    def _get_rebalance_dates(self, frequency: str) -> List[datetime]:
        """Generate dates for strategy evaluation."""
        dates = []
        current = self.start_date

        if frequency == "daily":
            while current <= self.end_date:
                dates.append(current)
                current += timedelta(days=1)
        elif frequency == "weekly":
            while current <= self.end_date:
                dates.append(current)
                current += timedelta(weeks=1)
        else:  # monthly
            while current <= self.end_date:
                dates.append(current)
                # Move to next month
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)

        return dates

    def _get_price_at_date(self, date: datetime) -> Optional[Dict]:
        """Get price record for a specific date (or nearest prior date)."""
        if not self._price_data:
            return None

        # Find the most recent price on or before the given date
        best_match = None
        best_match_date = None
        for record in self._price_data:
            record_date_str = record.get("date")
            if isinstance(record_date_str, str):
                try:
                    record_date = datetime.strptime(record_date_str, "%Y-%m-%d")
                except ValueError:
                    continue
            else:
                record_date = record_date_str

            if record_date <= date:
                if best_match is None or record_date > best_match_date:
                    best_match = record
                    best_match_date = record_date
            else:
                break

        return best_match

    def _get_financial_dates(self) -> Dict[str, datetime]:
        """Get the latest date for each financial dataset."""
        dates = {}
        for metric_name, data in self._financial_data.items():
            if data:
                latest = data[-1].get("date")
                if isinstance(latest, str):
                    try:
                        latest = datetime.strptime(latest, "%Y-%m-%d")
                    except ValueError:
                        continue
                dates[metric_name] = latest
        return dates

    def _get_available_financials(
        self,
        date: datetime,
        financial_dates: Dict[str, datetime]
    ) -> Dict[str, Any]:
        """
        Get financial data available up to the given date.

        This is critical for preventing look-ahead bias.
        We only use financial reports that were publicly available
        before the decision date.
        """
        available: Dict[str, Any] = {}

        for metric_name, cutoff_date in financial_dates.items():
            if cutoff_date <= date:
                # Find the most recent financial report before this date
                data_list = self._financial_data.get(metric_name, [])
                for record in reversed(data_list):
                    record_date = record.get("date")
                    if isinstance(record_date, str):
                        try:
                            record_date = datetime.strptime(record_date, "%Y-%m-%d")
                        except ValueError:
                            continue
                    if record_date <= date:
                        # Merge all metrics from this report
                        available.update(record)
                        break

        return available

    def _calculate_trade_value(
        self,
        cash: float,
        shares: int,
        price: float,
        signal: Signal
    ) -> float:
        """Calculate trade value based on signal and portfolio state."""
        if signal == Signal.BUY:
            # Invest 95% of cash (keep 5% buffer)
            return cash * 0.95
        elif signal == Signal.SELL:
            # Sell all shares
            return shares * price
        return 0

    def _get_portfolio_value(
        self,
        cash: float,
        shares: int,
        price: float
    ) -> float:
        """Calculate total portfolio value."""
        return cash + (shares * price)

    def _calculate_metrics(
        self,
        equity_curve: List[float],
        trades: List[Dict],
        initial_value: float,
        final_value: float,
    ) -> Dict[str, Optional[MetricResult]]:
        """Calculate all performance metrics."""
        metrics = {}

        # Total return
        metrics["total_return"] = calculate_total_return(initial_value, final_value)

        # Calculate periodic returns for other metrics
        returns = []
        for i in range(1, len(equity_curve)):
            if equity_curve[i-1] > 0:
                ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
                returns.append(ret)

        # Period length in years
        num_periods = len(equity_curve) - 1
        years = max(num_periods / 252, 1)  # Assume daily data

        # Annual return (CAGR)
        metrics["annual_return"] = calculate_cagr(initial_value, final_value, years)

        # Volatility
        metrics["volatility"] = calculate_volatility(returns)

        # Sharpe ratio
        metrics["sharpe_ratio"] = calculate_sharpe_ratio(returns)

        # Max drawdown
        metrics["max_drawdown"] = calculate_max_drawdown(equity_curve)

        # Win rate
        metrics["win_rate"] = calculate_win_rate(trades)

        # Turnover
        metrics["turnover"] = calculate_turnover(trades)

        return metrics

    def _run_benchmark(self) -> Optional[Dict]:
        """Run simple buy-and-hold benchmark."""
        if not self._benchmark_data:
            return None

        # Simple buy and hold
        initial_price = self._benchmark_data[0].get("close", 0)
        final_price = self._benchmark_data[-1].get("close", 0)

        if initial_price <= 0 or final_price <= 0:
            return None

        shares = self.initial_capital / initial_price
        final_value = shares * final_price
        total_return = (final_value - self.initial_capital) / self.initial_capital

        return {
            "total_return": total_return,
            "trades": [{
                "date": self._benchmark_data[0].get("date"),
                "action": "buy",
                "quantity": int(shares),
                "price": initial_price,
            }]
        }
