"""
Historical Financial Analysis Engine for idx-bei.

This module provides time-series analysis capabilities for financial data,
including:
- Quarterly and annual history tracking
- Year-over-year (YoY) growth calculations
- Quarter-over-quarter (QoQ) growth calculations
- Trailing twelve months (TTM) support
- Multi-period CAGR calculations

All calculations are deterministic and handle missing data gracefully.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from models import FinancialMetrics, FinancialPeriod, PeriodType
from normalization.mappings import normalize_field_name


@dataclass
class HistoricalRecord:
    """
    A single historical financial record for a company.

    Combines period information with normalized financial metrics.
    """
    period: FinancialPeriod
    metrics: FinancialMetrics

    @property
    def ticker(self) -> str:
        """Get the ticker from the period."""
        return self.period.ticker

    @property
    def date(self) -> Optional[date]:
        """Get the period end date."""
        return self.period.period_end

    @property
    def period_label(self) -> str:
        """Get human-readable period label."""
        return self.period.period_label

    def get_metric(self, metric_name: str) -> Optional[float]:
        """
        Get a specific metric value by name.

        Supports both normalized names and common aliases.
        """
        # Try direct access first
        if hasattr(self.metrics, metric_name):
            return getattr(self.metrics, metric_name)

        # Try normalized name mapping
        normalized = normalize_field_name(metric_name)
        if hasattr(self.metrics, normalized):
            return getattr(self.metrics, normalized)

        return None

    def __repr__(self) -> str:
        return f"HistoricalRecord(ticker={self.ticker}, period={self.period_label}, metrics={len(self.metrics.get_filled_metrics())} filled)"


@dataclass
class GrowthResult:
    """
    Result of a growth rate calculation.

    Contains the calculated growth rate along with the periods used.
    """
    value: Optional[float]
    metric_name: str
    start_period: Optional[str] = None
    end_period: Optional[str] = None
    start_value: Optional[float] = None
    end_value: Optional[float] = None
    years: Optional[int] = None
    notes: str = ""

    @property
    def is_available(self) -> bool:
        """Check if growth rate was successfully calculated."""
        return self.value is not None

    def __repr__(self) -> str:
        val_str = f"{self.value:.4f}" if self.value is not None else "N/A"
        return f"GrowthResult({self.metric_name}={val_str})"


class HistoricalFinancialData:
    """
    Manages historical financial data for a single company.

    Provides time-series analysis capabilities including growth calculations,
    trend analysis, and TTM computations.
    """

    def __init__(self, ticker: str):
        """
        Initialize historical financial data container.

        Args:
            ticker: Stock ticker symbol (e.g., "BBCA")
        """
        self.ticker = ticker.upper()
        self.records: List[HistoricalRecord] = []
        self._metrics_index: Dict[str, List[Tuple[int, Optional[float]]]] = {}

    def add_record(self, period: FinancialPeriod, metrics: FinancialMetrics) -> None:
        """
        Add a new historical record.

        Records are automatically sorted by period end date.

        Args:
            period: FinancialPeriod object
            metrics: FinancialMetrics object
        """
        record = HistoricalRecord(period=period, metrics=metrics)
        self.records.append(record)
        self._sort_records()

    def add_records_from_raw(self, raw_records: List[Dict]) -> None:
        """
        Add multiple records from raw dictionary data.

        Args:
            raw_records: List of raw financial data dictionaries
        """
        for raw in raw_records:
            # Extract period info. DB rows use ``period_end``; the IDX JSON feed
            # uses ``fsDate``/``fs_date``.
            fs_date = raw.get('fsDate') or raw.get('fs_date') or raw.get('period_end')
            period_end = None
            if fs_date:
                try:
                    period_end = date.fromisoformat(str(fs_date)[:10])
                except (ValueError, TypeError):
                    pass

            # Determine period type: an explicit fiscal_period wins; otherwise fall
            # back to the month heuristic used for the IDX JSON feed. Note: the
            # stored rows often lack fiscal_period, so a Sep-30 period_end is
            # treated as Q3 (it is ambiguous with a Sep fiscal-year end) — this
            # keeps partial-year snapshots out of the annual YoY comparison.
            period_type = PeriodType.ANNUAL
            fiscal_period = None
            explicit_period = raw.get('fiscal_period')
            if explicit_period is not None:
                period_type = PeriodType.QUARTERLY
                try:
                    fiscal_period = int(explicit_period)
                except (ValueError, TypeError):
                    fiscal_period = None
            elif period_end:
                month = period_end.month
                # Only auto-detect quarters for Mar, Jun, Sep (not Dec - Dec 31 is typically annual)
                if month in (3, 6, 9):
                    period_type = PeriodType.QUARTERLY
                    if month <= 3:
                        fiscal_period = 1
                    elif month <= 6:
                        fiscal_period = 2
                    else:
                        fiscal_period = 3

            period = FinancialPeriod(
                ticker=self.ticker,
                period_end=period_end,
                period_type=period_type,
                fiscal_period=fiscal_period
            )

            # Convert raw data to FinancialMetrics
            metrics = self._raw_to_metrics(raw)

            if metrics and not metrics.is_empty():
                self.add_record(period, metrics)

    def _raw_to_metrics(self, raw: Dict) -> FinancialMetrics:
        """Convert raw dictionary to FinancialMetrics object."""
        metrics = FinancialMetrics()

        # Map raw fields to normalized metrics. Keys cover BOTH the IDX JSON feed
        # (camelCase) and the PostgreSQL ``financial_ratios`` column names returned
        # by ``get_financial_ratio_history`` so neither source is silently dropped.
        field_mappings = {
            # IDX raw JSON
            'sales': 'revenue',
            'profitAttrOwner': 'net_income',
            'profit_period': 'net_income',
            'ebt': 'operating_income',
            'assets': 'total_assets',
            'liabilities': 'total_liabilities',
            'equity': 'total_equity',
            'eps': 'eps',
            'bookValue': 'total_equity',  # Sometimes used as equity proxy
            'roe': 'roe',
            'roa': 'roa',
            'de_ratio': 'debt_to_equity',
            'per': 'pe_ratio',
            'price_bv': 'pb_ratio',
            'npm': 'net_margin',
            # PostgreSQL financial_ratios columns
            'revenue': 'revenue',
            'net_income': 'net_income',
            'operating_income': 'operating_income',
            'gross_profit': 'gross_profit',
            'cost_of_goods_sold': 'cost_of_goods_sold',
            'interest_expense': 'interest_expense',
            'total_assets': 'total_assets',
            'total_liabilities': 'total_liabilities',
            'total_equity': 'total_equity',
            'total_debt': 'total_debt',
            'cash_and_equivalents': 'cash_and_equivalents',
            'operating_cash_flow': 'operating_cash_flow',
            'capital_expenditures': 'capital_expenditures',
            'roic': 'roic',
            'debt_to_equity': 'debt_to_equity',
            'current_ratio': 'current_ratio',
            'pe_ratio': 'pe_ratio',
            'pb_ratio': 'pb_ratio',
            'ev_ebitda': 'ev_ebitda',
            'net_margin': 'net_margin',
            'operating_margin': 'operating_margin',
            'gross_margin': 'gross_margin',
            'revenue_cagr': 'revenue_cagr_3y',
            'earnings_cagr': 'earnings_cagr_3y',
            'eps_cagr': 'eps_cagr_3y',
        }

        for raw_key, metric_name in field_mappings.items():
            if raw_key in raw and raw[raw_key] is not None:
                try:
                    value = float(raw[raw_key])
                    setattr(metrics, metric_name, value)
                except (ValueError, TypeError):
                    continue

        return metrics

    def _sort_records(self) -> None:
        """Sort records by period end date (most recent last)."""
        self.records.sort(key=lambda r: r.date or date.min)

    def get_latest(self) -> Optional[HistoricalRecord]:
        """Get the most recent financial record."""
        if not self.records:
            return None
        return self.records[-1]

    def get_historical(self, limit: Optional[int] = None) -> List[HistoricalRecord]:
        """
        Get historical records, optionally limited to N most recent.

        Args:
            limit: Maximum number of records to return (most recent)

        Returns:
            List of HistoricalRecord objects
        """
        if limit is None:
            return list(self.records)
        return list(self.records[-limit:])

    def get_metric_history(self, metric_name: str) -> List[Tuple[Optional[date], Optional[float]]]:
        """
        Get time series for a specific metric.

        Args:
            metric_name: Name of the metric (normalized or raw)

        Returns:
            List of (date, value) tuples, sorted chronologically
        """
        result = []
        for record in self.records:
            value = record.get_metric(metric_name)
            result.append((record.date, value))
        return result

    def calculate_yoy_growth(self, metric_name: str) -> GrowthResult:
        """
        Calculate year-over-year growth for a metric.

        Compares the most recent annual record with the prior year's annual record.

        Args:
            metric_name: Name of the metric to analyze

        Returns:
            GrowthResult with the calculated YoY growth rate
        """
        # Get annual records only
        annual_records = [r for r in self.records if r.period.period_type == PeriodType.ANNUAL]

        if len(annual_records) < 2:
            return GrowthResult(
                value=None,
                metric_name=metric_name,
                notes="Insufficient annual data for YoY comparison"
            )

        # Get two most recent annual records
        current = annual_records[-1]
        previous = annual_records[-2]

        current_value = current.get_metric(metric_name)
        previous_value = previous.get_metric(metric_name)

        if current_value is None or previous_value is None or previous_value == 0:
            return GrowthResult(
                value=None,
                metric_name=metric_name,
                start_period=previous.period_label,
                end_period=current.period_label,
                start_value=previous_value,
                end_value=current_value
            )

        # Calculate growth rate
        growth = (current_value - previous_value) / abs(previous_value)

        return GrowthResult(
            value=growth,
            metric_name=metric_name,
            start_period=previous.period_label,
            end_period=current.period_label,
            start_value=previous_value,
            end_value=current_value,
            years=1
        )

    def calculate_qoq_growth(self, metric_name: str) -> GrowthResult:
        """
        Calculate quarter-over-quarter growth for a metric.

        Compares the most recent quarter with the prior quarter.

        Args:
            metric_name: Name of the metric to analyze

        Returns:
            GrowthResult with the calculated QoQ growth rate
        """
        # Get quarterly records only
        quarterly_records = [r for r in self.records if r.period.period_type == PeriodType.QUARTERLY]

        if len(quarterly_records) < 2:
            return GrowthResult(
                value=None,
                metric_name=metric_name,
                notes="Insufficient quarterly data for QoQ comparison"
            )

        # Get two most recent quarterly records
        current = quarterly_records[-1]
        previous = quarterly_records[-2]

        current_value = current.get_metric(metric_name)
        previous_value = previous.get_metric(metric_name)

        if current_value is None or previous_value is None or previous_value == 0:
            return GrowthResult(
                value=None,
                metric_name=metric_name,
                start_period=previous.period_label,
                end_period=current.period_label,
                start_value=previous_value,
                end_value=current_value
            )

        growth = (current_value - previous_value) / abs(previous_value)

        return GrowthResult(
            value=growth,
            metric_name=metric_name,
            start_period=previous.period_label,
            end_period=current.period_label,
            start_value=previous_value,
            end_value=current_value,
            years=0.25  # One quarter
        )

    def calculate_cagr(self, metric_name: str, years: int = 5) -> GrowthResult:
        """
        Calculate Compound Annual Growth Rate (CAGR) for a metric.

        Args:
            metric_name: Name of the metric to analyze
            years: Number of years over which to calculate CAGR

        Returns:
            GrowthResult with the calculated CAGR
        """
        if len(self.records) < 2:
            return GrowthResult(
                value=None,
                metric_name=metric_name,
                notes="Insufficient data for CAGR calculation"
            )

        # Get the oldest and newest records
        oldest = self.records[0]
        newest = self.records[-1]

        start_value = oldest.get_metric(metric_name)
        end_value = newest.get_metric(metric_name)

        if start_value is None or end_value is None:
            return GrowthResult(
                value=None,
                metric_name=metric_name,
                start_period=oldest.period_label,
                end_period=newest.period_label,
                start_value=start_value,
                end_value=end_value
            )

        if start_value <= 0 or end_value <= 0:
            return GrowthResult(
                value=None,
                metric_name=metric_name,
                notes="CAGR requires positive values",
                start_value=start_value,
                end_value=end_value
            )

        # Calculate actual years between records
        if oldest.date and newest.date:
            actual_years = (newest.date - oldest.date).days / 365.25
            actual_years = max(actual_years, 1)
        else:
            actual_years = years

        # CAGR formula: (End/Start)^(1/years) - 1
        try:
            cagr = (end_value / start_value) ** (1 / actual_years) - 1
        except (ValueError, ZeroDivisionError):
            return GrowthResult(
                value=None,
                metric_name=metric_name,
                notes="Invalid values for CAGR calculation"
            )

        return GrowthResult(
            value=cagr,
            metric_name=metric_name,
            start_period=oldest.period_label,
            end_period=newest.period_label,
            start_value=start_value,
            end_value=end_value,
            years=int(actual_years)
        )

    def calculate_ttm(self, metric_name: str) -> Optional[float]:
        """
        Calculate Trailing Twelve Months (TTM) value for a metric.

        Sums the most recent 4 quarterly records.

        Args:
            metric_name: Name of the metric to sum

        Returns:
            TTM value or None if insufficient data
        """
        quarterly_records = [r for r in self.records
                            if r.period.period_type == PeriodType.QUARTERLY]

        if len(quarterly_records) < 4:
            return None

        # Get the 4 most recent quarters
        recent_quarters = quarterly_records[-4:]

        total = 0.0
        for record in recent_quarters:
            value = record.get_metric(metric_name)
            if value is not None:
                total += value

        return total if total != 0 else None

    def get_growth_summary(self, metrics: List[str]) -> Dict[str, GrowthResult]:
        """
        Get growth rates for multiple metrics at once.

        Args:
            metrics: List of metric names to analyze

        Returns:
            Dictionary mapping metric names to GrowthResult objects
        """
        return {
            metric: self.calculate_yoy_growth(metric)
            for metric in metrics
        }

    def get_trend(self, metric_name: str, direction: str = "improving") -> str:
        """
        Determine the trend direction for a metric.

        Args:
            metric_name: Name of the metric
            direction: "improving" (higher is better) or "declining" (lower is better)

        Returns:
            Trend indicator: "up", "down", or "stable"
        """
        history = self.get_metric_history(metric_name)

        # Filter out None values
        valid_history = [(d, v) for d, v in history if v is not None]

        if len(valid_history) < 2:
            return "insufficient_data"

        # Get latest and earliest values
        latest_value = valid_history[-1][1]
        earliest_value = valid_history[0][1]

        if earliest_value == 0:
            return "stable"

        change = (latest_value - earliest_value) / abs(earliest_value)

        if direction == "improving":
            if change > 0.1:  # More than 10% improvement
                return "up"
            elif change < -0.1:  # More than 10% decline
                return "down"
        else:  # declining
            if change < -0.1:
                return "up"  # Lower is better for this metric
            elif change > 0.1:
                return "down"

        return "stable"

    def get_period_count(self) -> int:
        """Get the number of historical periods."""
        return len(self.records)

    def has_annual_data(self) -> bool:
        """Check if annual data is available."""
        return any(r.period.period_type == PeriodType.ANNUAL for r in self.records)

    def has_quarterly_data(self) -> bool:
        """Check if quarterly data is available."""
        return any(r.period.period_type == PeriodType.QUARTERLY for r in self.records)

    def __repr__(self) -> str:
        return f"HistoricalFinancialData(ticker={self.ticker}, periods={len(self.records)})"


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_historical_data(ticker: str, raw_data: List[Dict]) -> HistoricalFinancialData:
    """
    Create a HistoricalFinancialData object from raw data.

    Args:
        ticker: Stock ticker symbol
        raw_data: List of raw financial data dictionaries

    Returns:
        HistoricalFinancialData object populated with the data
    """
    hfd = HistoricalFinancialData(ticker=ticker)
    hfd.add_records_from_raw(raw_data)
    return hfd


def analyze_company_growth(
    ticker: str,
    raw_data: List[Dict],
    metrics: Optional[List[str]] = None
) -> Dict[str, GrowthResult]:
    """
    Analyze growth rates for a company across multiple metrics.

    Args:
        ticker: Stock ticker symbol
        raw_data: List of raw financial data dictionaries
        metrics: List of metrics to analyze (defaults to key financial metrics)

    Returns:
        Dictionary of metric names to GrowthResult objects
    """
    if metrics is None:
        metrics = ['revenue', 'net_income', 'eps']

    hfd = create_historical_data(ticker, raw_data)
    return hfd.get_growth_summary(metrics)


def get_financial_trends(
    ticker: str,
    raw_data: List[Dict],
    metrics: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    Get trend directions for key financial metrics.

    Args:
        ticker: Stock ticker symbol
        raw_data: List of raw financial data dictionaries
        metrics: List of metrics to analyze

    Returns:
        Dictionary of metric names to trend strings ("up", "down", "stable")
    """
    if metrics is None:
        metrics = ['revenue', 'net_income', 'roe', 'debt_to_equity']

    hfd = create_historical_data(ticker, raw_data)

    trends = {}
    for metric in metrics:
        # Revenue, net income, ROE improve when going up
        # Debt-to-equity improves when going down
        direction = "improving" if metric not in ('debt_to_equity', 'net_debt_to_ebitda') else "declining"
        trends[metric] = hfd.get_trend(metric, direction)

    return trends
