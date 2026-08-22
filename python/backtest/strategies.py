"""
Strategy Interface and Implementations for Backtesting.

This module defines the strategy pattern for backtesting investment strategies.
Strategies determine when to buy/sell based on available data at each point in time.

Key principle: NO LOOK-Ahead bias. Strategies can only use information
that was available at the decision date.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class Signal(Enum):
    """Trading signals."""
    HOLD = "hold"
    BUY = "buy"
    SELL = "sell"


class StrategyType(Enum):
    """Types of strategies."""
    VALUE = "value"
    GROWTH = "growth"
    QUALITY = "quality"
    TECHNICAL = "technical"
    CUSTOM = "custom"


@dataclass
class Trade:
    """
    Represents a single trade execution.

    Attributes:
        date: Date of trade
        action: buy or sell
        ticker: Stock ticker
        quantity: Number of shares
        price: Execution price
        value: Total trade value
        reason: Reason for trade
    """
    date: datetime
    action: str
    ticker: str
    quantity: int
    price: float
    value: float
    reason: str
    portfolio_value: float = 0.0


@dataclass
class StrategyConfig:
    """
    Configuration for a backtesting strategy.

    Attributes:
        type: Strategy type
        name: Human-readable name
        parameters: Strategy-specific parameters
        rebalance_frequency: How often to rebalance (daily, weekly, monthly)
        transaction_cost: Cost per trade as decimal (e.g., 0.001 for 0.1%)
        slippage: Estimated slippage as decimal
    """
    type: StrategyType
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    rebalance_frequency: str = "monthly"
    transaction_cost: float = 0.001
    slippage: float = 0.0005


class Strategy(ABC):
    """
    Base class for all backtesting strategies.

    Subclasses must implement:
    - generate_signal(): Determine buy/sell/hold at each date
    - get_name(): Return strategy name
    - get_type(): Return strategy type
    """

    def __init__(self, config: Optional[StrategyConfig] = None):
        """
        Initialize the strategy.

        Args:
            config: Strategy configuration. If None, uses defaults.
        """
        self.config = config or StrategyConfig(
            type=StrategyType.CUSTOM,
            name=self.__class__.__name__,
        )
        self.trades: List[Trade] = []

    @abstractmethod
    def generate_signal(
        self,
        date: datetime,
        current_price: float,
        available_data: Dict[str, Any],
    ) -> Signal:
        """
        Generate a trading signal based on available data.

        IMPORTANT: Only use data that was available at the given date.
        This prevents look-ahead bias.

        Args:
            date: Current date being evaluated
            current_price: Current stock price
            available_data: Dict of financial data available up to this date

        Returns:
            Signal: BUY, SELL, or HOLD
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return strategy name."""
        pass

    @abstractmethod
    def get_type(self) -> StrategyType:
        """Return strategy type."""
        pass

    def add_trade(self, trade: Trade) -> None:
        """Record a trade execution."""
        self.trades.append(trade)

    def clear_trades(self) -> None:
        """Clear trade history for reuse."""
        self.trades = []


class ValueStrategy(Strategy):
    """
    Value investing strategy.

    Buys stocks with low P/E and P/B ratios, sells when undervalued.
    """

    def __init__(
        self,
        pe_max: float = 20.0,
        pb_max: float = 2.0,
        div_yield_min: float = 0.02,
        config: Optional[StrategyConfig] = None,
    ):
        """
        Initialize value strategy.

        Args:
            pe_max: Maximum P/E ratio to consider
            pb_max: Maximum P/B ratio to consider
            div_yield_min: Minimum dividend yield
            config: Optional config override
        """
        params = {
            "pe_max": pe_max,
            "pb_max": pb_max,
            "div_yield_min": div_yield_min,
        }
        super().__init__(config or StrategyConfig(
            type=StrategyType.VALUE,
            name="Value Strategy",
            parameters=params,
        ))
        self.pe_max = pe_max
        self.pb_max = pb_max
        self.div_yield_min = div_yield_min

    def generate_signal(
        self,
        date: datetime,
        current_price: float,
        available_data: Dict[str, Any],
    ) -> Signal:
        """
        Generate signal based on valuation metrics.

        Buys if P/E < threshold and P/B < threshold.
        Sells if P/E > 2*threshold or P/B > 2*threshold.
        """
        pe_ratio = available_data.get("pe_ratio")
        pb_ratio = available_data.get("pb_ratio")
        div_yield = available_data.get("dividend_yield")

        # Check valuation
        is_undervalued = False
        is_overvalued = False

        if pe_ratio is not None and pb_ratio is not None:
            if pe_ratio <= self.pe_max and pb_ratio <= self.pb_max:
                is_undervalued = True
            if pe_ratio > self.pe_max * 2 or pb_ratio > self.pb_max * 2:
                is_overvalued = True

        # Bonus for dividend yield
        if div_yield is not None and div_yield >= self.div_yield_min:
            is_undervalued = True

        if is_overvalued:
            return Signal.SELL
        elif is_undervalued:
            return Signal.BUY
        return Signal.HOLD

    def get_name(self) -> str:
        return self.config.name

    def get_type(self) -> StrategyType:
        return StrategyType.VALUE


class GrowthStrategy(Strategy):
    """
    Growth investing strategy.

    Buys stocks with high revenue and earnings growth.
    """

    def __init__(
        self,
        rev_growth_min: float = 0.10,
        earnings_growth_min: float = 0.15,
        config: Optional[StrategyConfig] = None,
    ):
        """
        Initialize growth strategy.

        Args:
            rev_growth_min: Minimum revenue growth rate
            earnings_growth_min: Minimum earnings growth rate
            config: Optional config override
        """
        params = {
            "rev_growth_min": rev_growth_min,
            "earnings_growth_min": earnings_growth_min,
        }
        super().__init__(config or StrategyConfig(
            type=StrategyType.GROWTH,
            name="Growth Strategy",
            parameters=params,
        ))
        self.rev_growth_min = rev_growth_min
        self.earnings_growth_min = earnings_growth_min

    def generate_signal(
        self,
        date: datetime,
        current_price: float,
        available_data: Dict[str, Any],
    ) -> Signal:
        """
        Generate signal based on growth metrics.

        Buys if revenue growth and earnings growth exceed thresholds.
        """
        rev_growth = available_data.get("revenue_growth")
        earnings_growth = available_data.get("earnings_growth")

        meets_revenue_growth = rev_growth is not None and rev_growth >= self.rev_growth_min
        meets_earnings_growth = earnings_growth is not None and earnings_growth >= self.earnings_growth_min

        if meets_revenue_growth and meets_earnings_growth:
            return Signal.BUY
        elif not meets_revenue_growth and not meets_earnings_growth:
            return Signal.SELL
        return Signal.HOLD

    def get_name(self) -> str:
        return self.config.name

    def get_type(self) -> StrategyType:
        return StrategyType.GROWTH


class QualityStrategy(Strategy):
    """
    Quality investing strategy.

    Buys stocks with high profitability and low debt.
    """

    def __init__(
        self,
        roe_min: float = 0.15,
        debt_to_equity_max: float = 1.0,
        net_margin_min: float = 0.10,
        config: Optional[StrategyConfig] = None,
    ):
        """
        Initialize quality strategy.

        Args:
            roe_min: Minimum ROE
            debt_to_equity_max: Maximum debt-to-equity ratio
            net_margin_min: Minimum net margin
            config: Optional config override
        """
        params = {
            "roe_min": roe_min,
            "debt_to_equity_max": debt_to_equity_max,
            "net_margin_min": net_margin_min,
        }
        super().__init__(config or StrategyConfig(
            type=StrategyType.QUALITY,
            name="Quality Strategy",
            parameters=params,
        ))
        self.roe_min = roe_min
        self.debt_to_equity_max = debt_to_equity_max
        self.net_margin_min = net_margin_min

    def generate_signal(
        self,
        date: datetime,
        current_price: float,
        available_data: Dict[str, Any],
    ) -> Signal:
        """
        Generate signal based on quality metrics.

        Buys if ROE, debt ratio, and margin meet criteria.
        """
        roe = available_data.get("roe")
        debt_equity = available_data.get("debt_to_equity")
        net_margin = available_data.get("net_margin")

        quality_score = 0
        quality_count = 0

        if roe is not None:
            quality_count += 1
            if roe >= self.roe_min:
                quality_score += 1

        if debt_equity is not None:
            quality_count += 1
            if debt_equity <= self.debt_to_equity_max:
                quality_score += 1

        if net_margin is not None:
            quality_count += 1
            if net_margin >= self.net_margin_min:
                quality_score += 1

        # Buy if majority of quality metrics are met
        if quality_count > 0 and quality_score / quality_count >= 0.67:
            return Signal.BUY
        elif quality_score == 0:
            return Signal.SELL
        return Signal.HOLD

    def get_name(self) -> str:
        return self.config.name

    def get_type(self) -> StrategyType:
        return StrategyType.QUALITY


class TechnicalStrategy(Strategy):
    """
    Technical analysis strategy.

    Uses moving averages and RSI for entry/exit signals.
    """

    def __init__(
        self,
        fast_ma: int = 20,
        slow_ma: int = 50,
        rsi_period: int = 14,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        config: Optional[StrategyConfig] = None,
    ):
        """
        Initialize technical strategy.

        Args:
            fast_ma: Fast moving average period
            slow_ma: Slow moving average period
            rsi_period: RSI calculation period
            rsi_oversold: RSI level for oversold
            rsi_overbought: RSI level for overbought
            config: Optional config override
        """
        params = {
            "fast_ma": fast_ma,
            "slow_ma": slow_ma,
            "rsi_period": rsi_period,
            "rsi_oversold": rsi_oversold,
            "rsi_overbought": rsi_overbought,
        }
        super().__init__(config or StrategyConfig(
            type=StrategyType.TECHNICAL,
            name="Technical Strategy",
            parameters=params,
        ))
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought

    def generate_signal(
        self,
        date: datetime,
        current_price: float,
        available_data: Dict[str, Any],
    ) -> Signal:
        """
        Generate signal based on technical indicators.

        Buys on golden cross (fast MA crosses above slow MA) or RSI oversold.
        Sells on death cross or RSI overbought.
        """
        fast_ma = available_data.get("fast_ma")
        slow_ma = available_data.get("slow_ma")
        rsi = available_data.get("rsi")

        # Moving average crossover
        ma_cross_signal = None
        if fast_ma is not None and slow_ma is not None:
            if fast_ma > slow_ma:
                ma_cross_signal = Signal.BUY
            else:
                ma_cross_signal = Signal.SELL

        # RSI signal
        rsi_signal = None
        if rsi is not None:
            if rsi <= self.rsi_oversold:
                rsi_signal = Signal.BUY
            elif rsi >= self.rsi_overbought:
                rsi_signal = Signal.SELL

        # Combine signals (both must agree for strong signal)
        if ma_cross_signal == Signal.BUY and rsi_signal == Signal.BUY:
            return Signal.BUY
        elif ma_cross_signal == Signal.SELL and rsi_signal == Signal.SELL:
            return Signal.SELL
        elif ma_cross_signal == Signal.BUY or rsi_signal == Signal.BUY:
            return Signal.BUY
        elif ma_cross_signal == Signal.SELL or rsi_signal == Signal.SELL:
            return Signal.SELL
        return Signal.HOLD

    def get_name(self) -> str:
        return self.config.name

    def get_type(self) -> StrategyType:
        return StrategyType.TECHNICAL
