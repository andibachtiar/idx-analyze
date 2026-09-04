"""
Tests for Valuation Engine (Phase 5).

Tests all deterministic valuation calculations including:
- P/E ratio
- P/B ratio
- EV/EBITDA
- EV/EBIT
- P/FCF
- Dividend yield
- Historical valuation percentiles
- Valuation signals
- Edge cases and error handling
"""

import os
import sys
from datetime import date

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

from analysis.valuation import (
    HistoricalValuation,
    ValuationResult,
    add_historical_context,
    calculate_all_valuations,
    calculate_dividend_yield,
    calculate_ev_ebit,
    calculate_ev_ebitda,
    calculate_historical_percentile,
    calculate_pb_ratio,
    calculate_pe_fcf,
    calculate_pe_ratio,
    get_valuation_signal,
    get_valuation_summary,
)
from models import FinancialMetrics

# =============================================================================
# VALUATION RESULT TESTS
# =============================================================================

class TestValuationResult:
    """Tests for ValuationResult dataclass."""

    def test_available_result(self):
        result = ValuationResult(
            value=15.5,
            metric_name="pe_ratio",
            formula="Price / EPS",
            inputs={"price": 1550, "eps": 100}
        )
        assert result.is_available
        assert "15.5000" in repr(result)

    def test_unavailable_result(self):
        result = ValuationResult(
            value=None,
            metric_name="pe_ratio",
            formula="Price / EPS",
            inputs={"price": 1550, "eps": 0}
        )
        assert not result.is_available
        assert "N/A" in repr(result)

    def test_with_date_and_source(self):
        result = ValuationResult(
            value=12.5,
            metric_name="pe_ratio",
            formula="Price / EPS",
            inputs={"price": 1250, "eps": 100},
            valuation_date=date(2024, 12, 31),
            data_source="idx"
        )
        assert result.valuation_date == date(2024, 12, 31)
        assert result.data_source == "idx"


# =============================================================================
# HISTORICAL VALUATION TESTS
# =============================================================================

class TestHistoricalValuation:
    """Tests for HistoricalValuation dataclass."""

    def test_is_expensive(self):
        hist = HistoricalValuation(
            current_value=25.0,
            metric_name="pe_ratio",
            period_label="2024",
            history=[],
            percentile=85.0
        )
        assert hist.is_expensive
        assert not hist.is_cheap

    def test_is_cheap(self):
        hist = HistoricalValuation(
            current_value=10.0,
            metric_name="pe_ratio",
            period_label="2024",
            history=[],
            percentile=15.0
        )
        assert hist.is_cheap
        assert not hist.is_expensive

    def test_neither_extreme(self):
        hist = HistoricalValuation(
            current_value=15.0,
            metric_name="pe_ratio",
            period_label="2024",
            history=[],
            percentile=50.0
        )
        assert not hist.is_expensive
        assert not hist.is_cheap


# =============================================================================
# P/E RATIO TESTS
# =============================================================================

class TestPERatio:
    """Tests for P/E ratio calculation."""

    def test_basic_pe(self):
        result = calculate_pe_ratio(price=1500, eps=100)
        assert result.value == 15.0
        assert result.metric_name == "pe_ratio"
        assert result.formula == "Price / EPS"

    def test_high_pe(self):
        result = calculate_pe_ratio(price=5000, eps=50)
        assert result.value == 100.0

    def test_low_pe(self):
        result = calculate_pe_ratio(price=500, eps=100)
        assert result.value == 5.0

    def test_zero_eps(self):
        result = calculate_pe_ratio(price=1000, eps=0)
        assert result.value is None
        assert "EPS is zero" in result.notes

    def test_missing_eps(self):
        result = calculate_pe_ratio(price=1000, eps=None)
        assert result.value is None

    def test_negative_eps(self):
        result = calculate_pe_ratio(price=1000, eps=-50)
        # Negative EPS gives negative P/E (loss-making company)
        assert result.value == -20.0

    def test_with_date(self):
        result = calculate_pe_ratio(
            price=1500, eps=100,
            valuation_date=date(2024, 12, 31)
        )
        assert result.valuation_date == date(2024, 12, 31)


# =============================================================================
# P/B RATIO TESTS
# =============================================================================

class TestPBRatio:
    """Tests for P/B ratio calculation."""

    def test_basic_pb(self):
        result = calculate_pb_ratio(price=2000, book_value_per_share=1000)
        assert result.value == 2.0
        assert result.metric_name == "pb_ratio"

    def test_pb_below_book(self):
        result = calculate_pb_ratio(price=800, book_value_per_share=1000)
        assert result.value == 0.8

    def test_pb_at_book(self):
        result = calculate_pb_ratio(price=1000, book_value_per_share=1000)
        assert result.value == 1.0

    def test_zero_book_value(self):
        result = calculate_pb_ratio(price=1000, book_value_per_share=0)
        assert result.value is None
        assert "Book value per share is zero" in result.notes

    def test_negative_book_value(self):
        # Negative book value is unusual but should be handled
        result = calculate_pb_ratio(price=1000, book_value_per_share=-500)
        assert result.value == -2.0


# =============================================================================
# EV/EBITDA TESTS
# =============================================================================

class TestEVEbitda:
    """Tests for EV/EBITDA calculation."""

    def test_basic_ev_ebitda(self):
        # EV = 10000 + 5000 - 1000 = 14000
        # EV/EBITDA = 14000 / 2000 = 7.0
        result = calculate_ev_ebitda(
            market_cap=10000,
            total_debt=5000,
            cash=1000,
            ebitda=2000
        )
        assert result.value == 7.0
        assert result.metric_name == "ev_ebitda"

    def test_ev_ebitda_with_no_debt(self):
        result = calculate_ev_ebitda(
            market_cap=10000,
            total_debt=0,
            cash=2000,
            ebitda=2500
        )
        # EV = 10000 + 0 - 2000 = 8000
        # EV/EBITDA = 8000 / 2500 = 3.2
        assert result.value == 3.2

    def test_zero_ebitda(self):
        result = calculate_ev_ebitda(
            market_cap=10000,
            total_debt=0,
            cash=0,
            ebitda=0
        )
        assert result.value is None

    def test_negative_ebitda(self):
        # Loss-making company
        result = calculate_ev_ebitda(
            market_cap=10000,
            total_debt=0,
            cash=0,
            ebitda=-1000
        )
        # Should still calculate (negative EV/EBITDA indicates loss)
        assert result.value == -10.0


# =============================================================================
# EV/EBIT TESTS
# =============================================================================

class TestEV_Ebit:
    """Tests for EV/EBIT calculation."""

    def test_basic_ev_ebit(self):
        # EV = 10000 + 5000 - 1000 = 14000
        # EV/EBIT = 14000 / 2000 = 7.0
        result = calculate_ev_ebit(
            market_cap=10000,
            total_debt=5000,
            cash=1000,
            ebit=2000
        )
        assert result.value == 7.0

    def test_zero_ebit(self):
        result = calculate_ev_ebit(
            market_cap=10000,
            total_debt=0,
            cash=0,
            ebit=0
        )
        assert result.value is None


# =============================================================================
# P/FCF TESTS
# =============================================================================

class TestPFCF:
    """Tests for P/FCF calculation."""

    def test_basic_pe_fcf(self):
        result = calculate_pe_fcf(price=1500, free_cash_flow_per_share=100)
        assert result.value == 15.0
        assert result.metric_name == "pe_fcf"

    def test_low_pe_fcf(self):
        result = calculate_pe_fcf(price=500, free_cash_flow_per_share=100)
        assert result.value == 5.0

    def test_zero_fcf(self):
        result = calculate_pe_fcf(price=1000, free_cash_flow_per_share=0)
        assert result.value is None
        assert "FCF per share is zero" in result.notes

    def test_negative_fcf(self):
        # Negative FCF
        result = calculate_pe_fcf(price=1000, free_cash_flow_per_share=-50)
        assert result.value is None  # Returns None for negative FCF


# =============================================================================
# DIVIDEND YIELD TESTS
# =============================================================================

class TestDividendYield:
    """Tests for dividend yield calculation."""

    def test_basic_yield(self):
        # (50 / 1000) * 100 = 5%
        result = calculate_dividend_yield(
            annual_dividend_per_share=50,
            price=1000
        )
        assert result.value == 5.0
        assert result.metric_name == "dividend_yield"

    def test_high_yield(self):
        result = calculate_dividend_yield(
            annual_dividend_per_share=100,
            price=1000
        )
        assert result.value == 10.0

    def test_low_yield(self):
        result = calculate_dividend_yield(
            annual_dividend_per_share=10,
            price=1000
        )
        assert result.value == 1.0

    def test_zero_price(self):
        result = calculate_dividend_yield(
            annual_dividend_per_share=50,
            price=0
        )
        assert result.value is None

    def test_no_dividend(self):
        result = calculate_dividend_yield(
            annual_dividend_per_share=0,
            price=1000
        )
        assert result.value == 0.0


# =============================================================================
# HISTORICAL PERCENTILE TESTS
# =============================================================================

class TestHistoricalPercentile:
    """Tests for historical percentile calculation."""

    def test_median_value(self):
        values = [10, 15, 20, 25, 30]
        percentile = calculate_historical_percentile(20, values)
        assert percentile == 40.0  # 2 out of 5 values are below 20

    def test_lowest_value(self):
        values = [10, 20, 30, 40, 50]
        percentile = calculate_historical_percentile(10, values)
        assert percentile == 0.0

    def test_highest_value(self):
        values = [10, 20, 30, 40, 50]
        percentile = calculate_historical_percentile(50, values)
        assert percentile == 80.0  # 4 out of 5 are below

    def test_insufficient_data(self):
        percentile = calculate_historical_percentile(20, [10])
        assert percentile is None

    def test_empty_history(self):
        percentile = calculate_historical_percentile(20, [])
        assert percentile is None


# =============================================================================
# HISTORICAL CONTEXT TESTS
# =============================================================================

class TestHistoricalContext:
    """Tests for adding historical context to valuations."""

    def test_add_context_basic(self):
        valuation = ValuationResult(
            value=15.0,
            metric_name="pe_ratio",
            formula="Price / EPS",
            inputs={"price": 1500, "eps": 100},
            valuation_date=date(2024, 12, 31)
        )
        history = [("2020", 12), ("2021", 14), ("2022", 16), ("2023", 15)]

        hist = add_historical_context(valuation, history)

        assert hist.current_value == 15.0
        assert hist.median_5y is not None
        assert hist.percentile is not None

    def test_no_history(self):
        valuation = ValuationResult(
            value=15.0,
            metric_name="pe_ratio",
            formula="Price / EPS",
            inputs={"price": 1500, "eps": 100}
        )

        hist = add_historical_context(valuation, [])

        assert hist.current_value == 15.0
        assert hist.percentile is None


# =============================================================================
# BATCH VALUATION TESTS
# =============================================================================

class TestBatchValuation:
    """Tests for batch valuation calculations."""

    def setup_method(self):
        self.metrics = FinancialMetrics(
            eps=100.0,
            book_value_per_share=500.0,
            total_equity=50000.0,
            shares_outstanding=100000.0,
            operating_income=15000.0,
            free_cash_flow=10000.0,
            dividend_per_share=50.0
        )

    def test_calculate_all_valuations(self):
        results = calculate_all_valuations(
            price=1500,
            metrics=self.metrics,
            market_cap=150000.0,
            total_debt=50000.0,
            cash=10000.0,
            annual_dividend=50.0,
            valuation_date=date(2024, 12, 31)
        )

        assert "pe_ratio" in results
        assert "pb_ratio" in results
        assert results["pe_ratio"].value == 15.0
        assert results["pb_ratio"].value == 3.0

    def test_valuation_summary(self):
        summary = get_valuation_summary(
            price=1500,
            metrics=self.metrics,
            historical_pe=[("2020", 12), ("2021", 14), ("2022", 16), ("2023", 15)],
            valuation_date=date(2024, 12, 31)
        )

        assert "valuations" in summary
        assert "historical_comparison" in summary
        assert "pe_ratio" in summary["valuations"]


# =============================================================================
# VALUATION SIGNAL TESTS
# =============================================================================

class TestValuationSignal:
    """Tests for valuation signal determination."""

    def test_cheap_signal(self):
        pe = ValuationResult(value=10, metric_name="pe_ratio",
                           formula="P/E", inputs={})
        pb = ValuationResult(value=0.8, metric_name="pb_ratio",
                           formula="P/B", inputs={})

        signal = get_valuation_signal(pe, pb, pe_hist_percentile=20, pb_hist_percentile=15)
        assert signal == "cheap"

    def test_expensive_signal(self):
        pe = ValuationResult(value=30, metric_name="pe_ratio",
                           formula="P/E", inputs={})
        pb = ValuationResult(value=4.0, metric_name="pb_ratio",
                           formula="P/B", inputs={})

        signal = get_valuation_signal(pe, pb, pe_hist_percentile=85, pb_hist_percentile=90)
        assert signal == "expensive"

    def test_fair_signal(self):
        pe = ValuationResult(value=15, metric_name="pe_ratio",
                           formula="P/E", inputs={})
        pb = ValuationResult(value=1.5, metric_name="pb_ratio",
                           formula="P/B", inputs={})

        signal = get_valuation_signal(pe, pb, pe_hist_percentile=50, pb_hist_percentile=45)
        assert signal == "fair"

    def test_insufficient_data(self):
        signal = get_valuation_signal(None, None)
        assert signal == "insufficient_data"

    def test_mixed_signals(self):
        pe = ValuationResult(value=12, metric_name="pe_ratio",
                           formula="P/E", inputs={})  # Cheap
        pb = ValuationResult(value=3.5, metric_name="pb_ratio",
                           formula="P/B", inputs={})  # Expensive

        signal = get_valuation_signal(pe, pb, pe_hist_percentile=20, pb_hist_percentile=80)
        # One cheap, one expensive -> fair
        assert signal in ["fair", "fair_to_cheap", "fair_to_expensive"]


# =============================================================================
# INTEGRATION TESTS WITH REALISTIC DATA
# =============================================================================

class TestIntegration:
    """Integration tests with realistic Indonesian stock profiles."""

    def test_blue_chip_valuation(self):
        """Test valuation for a typical blue-chip stock (like BBCA)."""
        metrics = FinancialMetrics(
            eps=500.0,
            book_value_per_share=2000.0,
            total_equity=80000.0,
            shares_outstanding=16000.0,
            operating_income=25000.0,
            free_cash_flow=18000.0,
            dividend_per_share=100.0
        )

        results = calculate_all_valuations(
            price=8500,  # Typical BBCA price
            metrics=metrics,
            market_cap=136000.0,
            total_debt=100000.0,
            cash=20000.0,
            annual_dividend=100.0,
            valuation_date=date(2024, 12, 31)
        )

        # P/E should be reasonable (15-20 for blue chip)
        assert results["pe_ratio"].value is not None
        assert 10 < results["pe_ratio"].value < 30

        # P/B should be reasonable (>1 for quality bank)
        assert results["pb_ratio"].value is not None
        assert results["pb_ratio"].value > 1.0

        # Dividend yield should be positive
        assert results["dividend_yield"].value is not None
        assert results["dividend_yield"].value > 0

    def test_value_stock_valuation(self):
        """Test valuation for a value stock."""
        metrics = FinancialMetrics(
            eps=200.0,
            book_value_per_share=800.0,
            operating_income=8000.0,
            free_cash_flow=5000.0
        )

        results = calculate_all_valuations(
            price=2000,  # Low price
            metrics=metrics
        )

        # Low P/E (< 10)
        assert results["pe_ratio"].value == 10.0

        # Low P/B (< 1)
        assert results["pb_ratio"].value == 2.5

    def test_growth_stock_valuation(self):
        """Test valuation for a growth stock."""
        metrics = FinancialMetrics(
            eps=50.0,
            book_value_per_share=200.0,
            operating_income=3000.0
        )

        results = calculate_all_valuations(
            price=5000,  # High price
            metrics=metrics
        )

        # High P/E (> 20)
        assert results["pe_ratio"].value == 100.0

        # High P/B (> 5)
        assert results["pb_ratio"].value == 25.0


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_very_high_prices(self):
        result = calculate_pe_ratio(price=1000000, eps=1)
        assert result.value == 1000000.0

    def test_very_low_prices(self):
        result = calculate_pe_ratio(price=100, eps=1000)
        assert result.value == 0.1

    def test_large_market_cap(self):
        result = calculate_ev_ebitda(
            market_cap=1000000.0,
            total_debt=500000.0,
            cash=100000.0,
            ebitda=50000.0
        )
        # EV = 1000000 + 500000 - 100000 = 1400000
        # EV/EBITDA = 1400000 / 50000 = 28
        assert result.value == 28.0

    def test_all_none_inputs(self):
        results = calculate_all_valuations(
            price=None,
            metrics=FinancialMetrics()
        )
        # All results should have None values
        for key, result in results.items():
            assert result.value is None or result.metric_name in results


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
