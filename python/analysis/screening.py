"""
Stock Screening Engine for idx-bei.

This module provides deterministic stock screening capabilities.
All screening is purely mathematical — no AI/LLM involvement in the
initial filtering process.

Screening criteria supported:
- ROE > X%
- Revenue growth > X%
- Earnings growth > X%
- P/E < X
- P/B < X
- Debt/Equity < X
- Dividend yield > X%
- Price > SMA200
- RSI range

Each screen returns structured results with filter details.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union


class ScreenOperator(Enum):
    """Comparison operators for screen filters."""
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    EQUAL = "="
    BETWEEN = "between"
    IN_RANGE = "range"  # For RSI-like range checks


@dataclass
class ScreenFilter:
    """
    A single screening filter criterion.

    Example: ScreenFilter(metric="roe", operator=">", value=0.15)
    means "ROE must be greater than 15%"
    """
    metric: str
    operator: ScreenOperator
    value: float
    description: str = ""

    def __post_init__(self):
        if not self.description:
            self.description = f"{self.metric} {self.operator.value} {self.value}"

    def check(self, actual_value: Optional[float]) -> Tuple[bool, str]:
        """
        Check if a value passes this filter.

        Returns:
            Tuple of (passed, reason)
        """
        if actual_value is None:
            return False, f"Missing {self.metric} data"

        try:
            # Handle string comparison
            if isinstance(actual_value, str) or isinstance(self.value, str):
                passed = str(actual_value) == str(self.value)
                reason = f"{self.metric}={actual_value} {'==' if passed else '!='} {self.value}"
                return passed, reason

            # Numeric comparisons
            if self.operator == ScreenOperator.GREATER_THAN:
                passed = actual_value > self.value
                reason = f"{self.metric}={actual_value:.4f} {'>' if passed else '<'} {self.value}"
            elif self.operator == ScreenOperator.LESS_THAN:
                passed = actual_value < self.value
                reason = f"{self.metric}={actual_value:.4f} {'<' if passed else '>'} {self.value}"
            elif self.operator == ScreenOperator.GREATER_EQUAL:
                passed = actual_value >= self.value
                reason = f"{self.metric}={actual_value:.4f} {'>=' if passed else '<'} {self.value}"
            elif self.operator == ScreenOperator.LESS_EQUAL:
                passed = actual_value <= self.value
                reason = f"{self.metric}={actual_value:.4f} {'<=' if passed else '>'} {self.value}"
            elif self.operator == ScreenOperator.EQUAL:
                passed = actual_value == self.value
                reason = f"{self.metric}={actual_value:.4f} {'==' if passed else '!='} {self.value}"
            elif self.operator == ScreenOperator.BETWEEN:
                passed = self.value[0] <= actual_value <= self.value[1]
                reason = f"{self.metric}={actual_value:.4f} in [{self.value[0]}, {self.value[1]}]"
            elif self.operator == ScreenOperator.IN_RANGE:
                low, high = self.value
                passed = low <= actual_value <= high
                reason = f"{self.metric}={actual_value:.4f} in range [{low}, {high}]"
            else:
                passed = False
                reason = f"Unknown operator: {self.operator}"

            return passed, reason
        except (TypeError, IndexError):
            return False, f"Invalid filter value for {self.metric}"

    def __repr__(self) -> str:
        return f"ScreenFilter({self.description})"


@dataclass
class StockResult:
    """
    Result of screening a single stock.

    Contains the ticker, passing status, and details about each filter.
    """
    ticker: str
    name: str
    passed: bool
    filters: Dict[str, Tuple[bool, str]] = field(default_factory=dict)
    score: float = 0.0
    metadata: Dict = field(default_factory=dict)

    @property
    def passing_filters(self) -> int:
        """Count of passing filters."""
        return sum(1 for passed, _ in self.filters.values() if passed)

    @property
    def total_filters(self) -> int:
        """Total number of filters applied."""
        return len(self.filters)

    @property
    def pass_rate(self) -> float:
        """Percentage of filters passed."""
        if self.total_filters == 0:
            return 0.0
        return (self.passing_filters / self.total_filters) * 100

    def __repr__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"StockResult({self.ticker}: {status}, {self.passing_filters}/{self.total_filters})"


@dataclass
class ScreenResult:
    """
    Result of running a complete stock screen.

    Contains all screened stocks and summary statistics.
    """
    filters: List[ScreenFilter]
    results: List[StockResult]
    total_stocks_screened: int
    stocks_passed: int
    run_date: date
    notes: str = ""

    @property
    def pass_rate(self) -> float:
        """Overall pass rate across all stocks."""
        if self.total_stocks_screened == 0:
            return 0.0
        return (self.stocks_passed / self.total_stocks_screened) * 100

    def get_passed_stocks(self) -> List[StockResult]:
        """Get list of stocks that passed all filters."""
        return [r for r in self.results if r.passed]

    def get_failed_stocks(self) -> List[StockResult]:
        """Get list of stocks that failed at least one filter."""
        return [r for r in self.results if not r.passed]

    def __repr__(self) -> str:
        return f"ScreenResult({self.stocks_passed}/{self.total_stocks_screened} passed)"


# =============================================================================
# SCREENING ENGINE
# =============================================================================

class StockScreeningEngine:
    """
    Main engine for stock screening.

    Applies multiple filters to a universe of stocks and returns
    structured results.
    """

    def __init__(self):
        self._stock_data: Dict[str, Dict] = {}

    def add_stock(self, ticker: str, data: Dict) -> None:
        """
        Add stock data for screening.

        Args:
            ticker: Stock ticker symbol
            data: Dictionary containing financial metrics and prices
        """
        self._stock_data[ticker] = data

    def add_stocks(self, stocks: Dict[str, Dict]) -> None:
        """
        Add multiple stocks for screening.

        Args:
            stocks: Dictionary mapping tickers to stock data
        """
        self._stock_data.update(stocks)

    def remove_stock(self, ticker: str) -> bool:
        """Remove a stock from the screening universe."""
        if ticker in self._stock_data:
            del self._stock_data[ticker]
            return True
        return False

    def screen(
        self,
        filters: List[ScreenFilter],
        min_pass_rate: float = 100.0
    ) -> ScreenResult:
        """
        Run screening against all stocks in the universe.

        Args:
            filters: List of ScreenFilter objects defining criteria
            min_pass_rate: Minimum percentage of filters that must pass

        Returns:
            ScreenResult with all screening outcomes
        """
        results = []

        for ticker, data in self._stock_data.items():
            result = self._screen_single_stock(ticker, data, filters)
            results.append(result)

        # Sort by pass rate (highest first), then by ticker
        results.sort(key=lambda x: (-x.pass_rate, x.ticker))

        # Filter by minimum pass rate
        filtered_results = [
            r for r in results
            if r.pass_rate >= min_pass_rate or r.passed
        ]

        return ScreenResult(
            filters=filters,
            results=filtered_results,
            total_stocks_screened=len(self._stock_data),
            stocks_passed=sum(1 for r in filtered_results if r.passed),
            run_date=date.today()
        )

    def _screen_single_stock(
        self,
        ticker: str,
        data: Dict,
        filters: List[ScreenFilter]
    ) -> StockResult:
        """Screen a single stock against all filters."""
        filter_results = {}

        for filter_obj in filters:
            metric_name = filter_obj.metric
            actual_value = data.get(metric_name)
            passed, reason = filter_obj.check(actual_value)
            filter_results[metric_name] = (passed, reason)

        # Determine overall pass/fail
        all_passed = all(passed for passed, _ in filter_results.values())

        # Calculate composite score (weighted average of normalized values)
        score = self._calculate_score(data, filters)

        return StockResult(
            ticker=ticker,
            name=data.get('name', ticker),
            passed=all_passed,
            filters=filter_results,
            score=score,
            metadata=data.get('metadata', {})
        )

    def _calculate_score(
        self,
        data: Dict,
        filters: List[ScreenFilter]
    ) -> float:
        """
        Calculate a composite screening score.

        Higher scores indicate stronger overall fit to criteria.
        """
        if not filters:
            return 0.0

        scores = []
        for filter_obj in filters:
            metric_name = filter_obj.metric
            value = data.get(metric_name)

            if value is None:
                scores.append(0.0)
                continue

            op = filter_obj.operator
            # Normalize each filter to a 0..2 scale where 1.0 is "meets the
            # threshold exactly". The curve is smooth and non-saturating so a
            # stock that clears a threshold by a wide margin scores higher than
            # one that barely clears it (a fixed min(value/threshold, 2.0) cap
            # made every passing stock look identical, e.g. all technical
            # screens showed the same 1.667).
            if op in (ScreenOperator.GREATER_THAN, ScreenOperator.GREATER_EQUAL):
                base = filter_obj.value
                if base and base > 0:
                    normalized = 2.0 * value / (base + value)
                else:
                    # Zero threshold (e.g. "price >= SMA200"): rank by the raw
                    # magnitude so 0.58 above the average beats 0.02.
                    normalized = min(2.0, 1.0 + value) if value >= 0 else 1.0
            elif op in (ScreenOperator.LESS_THAN, ScreenOperator.LESS_EQUAL):
                base = filter_obj.value
                if base and base > 0:
                    normalized = 2.0 * base / (base + value)
                else:
                    normalized = 2.0
            elif op in (ScreenOperator.IN_RANGE, ScreenOperator.BETWEEN):
                lo, hi = filter_obj.value[0], filter_obj.value[1]
                mid = (lo + hi) / 2.0
                half = max((hi - lo) / 2.0, 1e-9)
                closeness = max(0.0, 1.0 - abs(value - mid) / half)
                normalized = 1.0 + closeness
            else:
                normalized = 1.0

            scores.append(normalized)

        return sum(scores) / len(scores) if scores else 0.0

    def get_universe_size(self) -> int:
        """Get the number of stocks in the screening universe."""
        return len(self._stock_data)

    def get_stock_data(self, ticker: str) -> Optional[Dict]:
        """Get data for a specific stock."""
        return self._stock_data.get(ticker)

    def list_stocks(self) -> List[str]:
        """List all tickers in the screening universe."""
        return sorted(self._stock_data.keys())


# =============================================================================
# PREDEFINED SCREENS
# =============================================================================

def create_buffett_screen(
    roe_min: float = 0.15,
    de_max: float = 1.0,
    pe_max: float = 20.0,
    pb_max: float = 3.0,
    dividend_yield_min: float = 0.0
) -> List[ScreenFilter]:
    """
    Create a Buffett-style screening criteria.

    Classic Buffett criteria:
    - ROE >= 15%
    - Debt/Equity <= 1.0
    - P/E <= 20
    - P/B <= 3.0
    - Positive dividend yield (optional)

    Returns:
        List of ScreenFilter objects
    """
    filters = [
        ScreenFilter("roe", ScreenOperator.GREATER_EQUAL, roe_min, "ROE >= 15%"),
        ScreenFilter("debt_to_equity", ScreenOperator.LESS_EQUAL, de_max, "D/E <= 1.0"),
        ScreenFilter("pe_ratio", ScreenOperator.LESS_EQUAL, pe_max, "P/E <= 20"),
        ScreenFilter("pb_ratio", ScreenOperator.LESS_EQUAL, pb_max, "P/B <= 3.0"),
    ]

    if dividend_yield_min > 0:
        filters.append(
            ScreenFilter("dividend_yield", ScreenOperator.GREATER_EQUAL, dividend_yield_min, "Div Yield >= 0%")
        )

    return filters


def create_growth_screen(
    revenue_growth_min: float = 0.10,
    earnings_growth_min: float = 0.10,
    roe_min: float = 0.12,
    pe_max: float = 30.0
) -> List[ScreenFilter]:
    """
    Create a growth-oriented screening criteria.

    Focus on companies with strong growth metrics:
    - Revenue growth >= 10%
    - Earnings growth >= 10%
    - ROE >= 12%
    - P/E <= 30

    Returns:
        List of ScreenFilter objects
    """
    return [
        ScreenFilter("revenue_cagr", ScreenOperator.GREATER_EQUAL, revenue_growth_min, "Rev Growth >= 10%"),
        ScreenFilter("earnings_cagr", ScreenOperator.GREATER_EQUAL, earnings_growth_min, "Earn Growth >= 10%"),
        ScreenFilter("roe", ScreenOperator.GREATER_EQUAL, roe_min, "ROE >= 12%"),
        ScreenFilter("pe_ratio", ScreenOperator.LESS_EQUAL, pe_max, "P/E <= 30"),
    ]


def create_value_screen(
    pe_min: float = 0.0,
    pe_max: float = 15.0,
    pb_min: float = 0.0,
    pb_max: float = 1.5,
    dividend_yield_min: float = 2.0,
    debt_to_equity_max: float = 0.5
) -> List[ScreenFilter]:
    """
    Create a value-oriented screening criteria.

    Focus on undervalued stocks with dividends:
    - P/E between 0 and 15
    - P/B between 0 and 1.5
    - Dividend yield >= 2%
    - Debt/Equity <= 0.5

    Returns:
        List of ScreenFilter objects
    """
    return [
        ScreenFilter("pe_ratio", ScreenOperator.BETWEEN, (pe_min, pe_max), "P/E in range"),
        ScreenFilter("pb_ratio", ScreenOperator.BETWEEN, (pb_min, pb_max), "P/B in range"),
        ScreenFilter("dividend_yield", ScreenOperator.GREATER_EQUAL, dividend_yield_min, "Div Yield >= 2%"),
        ScreenFilter("debt_to_equity", ScreenOperator.LESS_EQUAL, debt_to_equity_max, "D/E <= 0.5"),
    ]


def create_quality_screen(
    roe_min: float = 0.15,
    roa_min: float = 0.08,
    debt_to_equity_max: float = 0.5,
    current_ratio_min: float = 1.5,
    net_margin_min: float = 0.10
) -> List[ScreenFilter]:
    """
    Create a quality-focused screening criteria.

    Focus on financially healthy companies:
    - ROE >= 15%
    - ROA >= 8%
    - Debt/Equity <= 0.5
    - Current Ratio >= 1.5
    - Net Margin >= 10%

    Returns:
        List of ScreenFilter objects
    """
    return [
        ScreenFilter("roe", ScreenOperator.GREATER_EQUAL, roe_min, "ROE >= 15%"),
        ScreenFilter("roa", ScreenOperator.GREATER_EQUAL, roa_min, "ROA >= 8%"),
        ScreenFilter("debt_to_equity", ScreenOperator.LESS_EQUAL, debt_to_equity_max, "D/E <= 0.5"),
        ScreenFilter("current_ratio", ScreenOperator.GREATER_EQUAL, current_ratio_min, "Current Ratio >= 1.5"),
        ScreenFilter("net_margin", ScreenOperator.GREATER_EQUAL, net_margin_min, "Net Margin >= 10%"),
    ]


def create_technical_screen(
    price_above_sma200: bool = True,
    rsi_min: float = 30.0,
    rsi_max: float = 70.0,
    volume_ratio_min: float = 0.5
) -> List[ScreenFilter]:
    """
    Create a technical analysis screening criteria.

    Focus on technical indicators:
    - Price above SMA200 (uptrend)
    - RSI between 30 and 70 (not extreme)
    - Volume ratio above minimum

    Returns:
        List of ScreenFilter objects
    """
    filters = []

    if price_above_sma200:
        filters.append(ScreenFilter("price_vs_sma_200", ScreenOperator.GREATER_EQUAL, 0, "Price >= SMA200"))

    filters.append(ScreenFilter("rsi_14", ScreenOperator.IN_RANGE, (rsi_min, rsi_max), "RSI in range"))

    if volume_ratio_min > 0:
        filters.append(ScreenFilter("volume_ratio", ScreenOperator.GREATER_EQUAL, volume_ratio_min, "Vol Ratio >= min"))

    return filters


def create_dividend_screen(
    dividend_yield_min: float = 3.0,
    payout_ratio_max: float = 0.80,
    roe_min: float = 0.10,
    debt_to_equity_max: float = 1.0
) -> List[ScreenFilter]:
    """
    Create a dividend-focused screening criteria.

    Focus on dividend-paying stocks:
    - Dividend yield >= 3%
    - Payout ratio <= 80%
    - ROE >= 10%
    - Debt/Equity <= 1.0

    Returns:
        List of ScreenFilter objects
    """
    return [
        ScreenFilter("dividend_yield", ScreenOperator.GREATER_EQUAL, dividend_yield_min, "Div Yield >= 3%"),
        ScreenFilter("payout_ratio", ScreenOperator.LESS_EQUAL, payout_ratio_max, "Payout <= 80%"),
        ScreenFilter("roe", ScreenOperator.GREATER_EQUAL, roe_min, "ROE >= 10%"),
        ScreenFilter("debt_to_equity", ScreenOperator.LESS_EQUAL, debt_to_equity_max, "D/E <= 1.0"),
    ]


# =============================================================================
# SCREENING RESULTS FORMATTING
# =============================================================================

def format_screen_results(screen_result: ScreenResult, top_n: Optional[int] = None) -> Dict:
    """
    Format screen results for display.

    Args:
        screen_result: The ScreenResult object
        top_n: Optional limit on number of results to show

    Returns:
        Formatted dictionary ready for display
    """
    output = {
        "run_date": screen_result.run_date.isoformat(),
        "total_stocks": screen_result.total_stocks_screened,
        "stocks_passed": screen_result.stocks_passed,
        "pass_rate": screen_result.pass_rate,
        "filters_applied": [f.description for f in screen_result.filters],
        "passed_stocks": [],
        "failed_stocks": []
    }

    passed = screen_result.get_passed_stocks()
    failed = screen_result.get_failed_stocks()

    if top_n:
        passed = passed[:top_n]
        # Show top failures for context
        failed = sorted(failed, key=lambda x: x.pass_rate)[:min(10, len(failed))]

    for stock in passed:
        output["passed_stocks"].append({
            "ticker": stock.ticker,
            "name": stock.name,
            "score": stock.score,
            "filters_passed": stock.passing_filters,
            "filters_total": stock.total_filters
        })

    for stock in failed[:20]:  # Limit failed display
        failing_reasons = [
            reason for passed, reason in stock.filters.values() if not passed
        ]
        output["failed_stocks"].append({
            "ticker": stock.ticker,
            "name": stock.name,
            "pass_rate": stock.pass_rate,
            "failing_reasons": failing_reasons[:3]  # Top 3 failures
        })

    return output


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def screen_stocks(
    stocks: Dict[str, Dict],
    filters: List[ScreenFilter],
    min_pass_rate: float = 100.0
) -> ScreenResult:
    """
    Convenience function to screen a dictionary of stocks.

    Args:
        stocks: Dictionary mapping tickers to stock data
        filters: List of screening filters
        min_pass_rate: Minimum pass rate threshold

    Returns:
        ScreenResult with screening outcomes
    """
    engine = StockScreeningEngine()
    engine.add_stocks(stocks)
    return engine.screen(filters, min_pass_rate)


def quick_screen(
    stocks: Dict[str, Dict],
    screen_type: str = "buffett",
    **kwargs
) -> ScreenResult:
    """
    Quick screening with predefined screen types.

    Available screen types:
    - "buffett": Classic Buffett criteria
    - "growth": Growth-oriented screening
    - "value": Value-oriented screening
    - "quality": Quality-focused screening
    - "technical": Technical analysis screening
    - "dividend": Dividend-focused screening

    Args:
        stocks: Dictionary mapping tickers to stock data
        screen_type: Type of screen to apply
        **kwargs: Additional parameters for the screen

    Returns:
        ScreenResult with screening outcomes
    """
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
        raise ValueError(f"Unknown screen type: {screen_type}")

    filters = creator(**kwargs)
    return screen_stocks(stocks, filters)
