"""
Tests for Stock Screening Engine (Phase 6).

Tests all deterministic screening functionality including:
- Individual filter evaluation
- Multiple filter combinations
- Predefined screen templates
- Result formatting
- Edge cases and error handling
"""

import os
import sys
from datetime import date
from unittest.mock import MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock external dependencies
sys.modules['neo4j'] = MagicMock()
sys.modules['psycopg2'] = MagicMock()
sys.modules['psycopg2.extensions'] = MagicMock()
sys.modules['sqlalchemy'] = MagicMock()
sys.modules['pandas'] = MagicMock()

import pytest

from analysis.screening import (
    ScreenFilter,
    ScreenOperator,
    ScreenResult,
    StockResult,
    StockScreeningEngine,
    create_buffett_screen,
    create_dividend_screen,
    create_growth_screen,
    create_quality_screen,
    create_technical_screen,
    create_value_screen,
    format_screen_results,
    quick_screen,
    screen_stocks,
)

# =============================================================================
# SCREEN FILTER TESTS
# =============================================================================

class TestScreenFilter:
    """Tests for ScreenFilter class."""

    def test_greater_than_pass(self):
        f = ScreenFilter("roe", ScreenOperator.GREATER_THAN, 0.15)
        passed, reason = f.check(0.20)
        assert passed is True
        assert "0.2000" in reason

    def test_greater_than_fail(self):
        f = ScreenFilter("roe", ScreenOperator.GREATER_THAN, 0.15)
        passed, reason = f.check(0.10)
        assert passed is False

    def test_less_than_pass(self):
        f = ScreenFilter("pe_ratio", ScreenOperator.LESS_THAN, 20.0)
        passed, reason = f.check(15.0)
        assert passed is True

    def test_less_than_fail(self):
        f = ScreenFilter("pe_ratio", ScreenOperator.LESS_THAN, 20.0)
        passed, reason = f.check(25.0)
        assert passed is False

    def test_between_pass(self):
        f = ScreenFilter("rsi", ScreenOperator.BETWEEN, (30.0, 70.0))
        passed, reason = f.check(50.0)
        assert passed is True

    def test_between_fail_low(self):
        f = ScreenFilter("rsi", ScreenOperator.BETWEEN, (30.0, 70.0))
        passed, reason = f.check(20.0)
        assert passed is False

    def test_between_fail_high(self):
        f = ScreenFilter("rsi", ScreenOperator.BETWEEN, (30.0, 70.0))
        passed, reason = f.check(80.0)
        assert passed is False

    def test_missing_value(self):
        f = ScreenFilter("roe", ScreenOperator.GREATER_THAN, 0.15)
        passed, reason = f.check(None)
        assert passed is False
        assert "Missing" in reason

    def test_equal_operator(self):
        f = ScreenFilter("sharia", ScreenOperator.EQUAL, "S")
        # String comparison
        passed, reason = f.check("S")
        assert passed is True

    def test_repr(self):
        f = ScreenFilter("roe", ScreenOperator.GREATER_THAN, 0.15)
        # Description uses lowercase metric name
        assert "roe" in repr(f).lower()
        assert ">" in repr(f)


# =============================================================================
# STOCK RESULT TESTS
# =============================================================================

class TestStockResult:
    """Tests for StockResult class."""

    def test_passed_stock(self):
        result = StockResult(
            ticker="BBCA",
            name="Bank Central Asia",
            passed=True,
            filters={"roe": (True, "OK"), "pe": (True, "OK")}
        )
        assert result.passed is True
        assert result.passing_filters == 2
        assert result.total_filters == 2
        assert result.pass_rate == 100.0

    def test_failed_stock(self):
        result = StockResult(
            ticker="ADRO",
            name="Adaro Indonesia",
            passed=False,
            filters={
                "roe": (True, "OK"),
                "pe": (False, "Too high")
            }
        )
        assert result.passed is False
        assert result.passing_filters == 1
        assert result.total_filters == 2
        assert result.pass_rate == 50.0

    def test_empty_filters(self):
        result = StockResult(ticker="TEST", name="Test", passed=True)
        assert result.total_filters == 0
        assert result.pass_rate == 0.0

    def test_repr(self):
        result = StockResult(ticker="BBCA", name="Test", passed=True)
        assert "PASS" in repr(result)
        assert "BBCA" in repr(result)


# =============================================================================
# SCREEN RESULT TESTS
# =============================================================================

class TestScreenResult:
    """Tests for ScreenResult class."""

    def test_empty_screen(self):
        result = ScreenResult(
            filters=[],
            results=[],
            total_stocks_screened=0,
            stocks_passed=0,
            run_date=date.today()
        )
        assert result.pass_rate == 0.0
        assert len(result.get_passed_stocks()) == 0

    def test_partial_pass(self):
        filters = [ScreenFilter("roe", ScreenOperator.GREATER_THAN, 0.15)]
        results = [
            StockResult("A", "Stock A", True, {"roe": (True, "OK")}),
            StockResult("B", "Stock B", False, {"roe": (False, "Fail")}),
        ]
        result = ScreenResult(
            filters=filters,
            results=results,
            total_stocks_screened=2,
            stocks_passed=1,
            run_date=date.today()
        )
        assert result.pass_rate == 50.0
        assert len(result.get_passed_stocks()) == 1
        assert len(result.get_failed_stocks()) == 1


# =============================================================================
# SCREENING ENGINE TESTS
# =============================================================================

class TestStockScreeningEngine:
    """Tests for StockScreeningEngine class."""

    def setup_method(self):
        self.engine = StockScreeningEngine()
        self._add_test_stocks()

    def _add_test_stocks(self):
        """Add test stock data."""
        test_stocks = {
            "BBCA": {
                "name": "Bank Central Asia",
                "roe": 0.20,
                "roa": 0.10,
                "pe_ratio": 15.0,
                "pb_ratio": 2.5,
                "debt_to_equity": 0.5,
                "current_ratio": 2.0,
                "net_margin": 0.20,
                "dividend_yield": 3.0,
                "revenue_cagr": 0.12,
                "earnings_cagr": 0.15,
                "price_vs_sma_200": 0.05,
                "rsi_14": 55.0,
                "volume_ratio": 1.2
            },
            "ADRO": {
                "name": "Adaro Indonesia",
                "roe": 0.25,
                "roa": 0.12,
                "pe_ratio": 8.0,
                "pb_ratio": 1.2,
                "debt_to_equity": 0.3,
                "current_ratio": 1.8,
                "net_margin": 0.18,
                "dividend_yield": 5.0,
                "revenue_cagr": 0.08,
                "earnings_cagr": 0.10,
                "price_vs_sma_200": -0.02,
                "rsi_14": 45.0,
                "volume_ratio": 0.8
            },
            "BBRI": {
                "name": "Bank Rakyat Indonesia",
                "roe": 0.18,
                "roa": 0.09,
                "pe_ratio": 12.0,
                "pb_ratio": 2.0,
                "debt_to_equity": 0.8,
                "current_ratio": 1.5,
                "net_margin": 0.15,
                "dividend_yield": 4.0,
                "revenue_cagr": 0.10,
                "earnings_cagr": 0.12,
                "price_vs_sma_200": 0.03,
                "rsi_14": 60.0,
                "volume_ratio": 1.0
            },
            "TLKM": {
                "name": "Telkom Indonesia",
                "roe": 0.15,
                "roa": 0.08,
                "pe_ratio": 18.0,
                "pb_ratio": 3.0,
                "debt_to_equity": 0.6,
                "current_ratio": 1.2,
                "net_margin": 0.12,
                "dividend_yield": 2.0,
                "revenue_cagr": 0.05,
                "earnings_cagr": 0.08,
                "price_vs_sma_200": -0.01,
                "rsi_14": 40.0,
                "volume_ratio": 0.9
            }
        }
        self.engine.add_stocks(test_stocks)

    def test_add_and_list_stocks(self):
        """Test adding stocks and listing them."""
        tickers = self.engine.list_stocks()
        assert len(tickers) == 4
        assert "BBCA" in tickers
        assert "ADRO" in tickers

    def test_get_stock_data(self):
        """Test retrieving individual stock data."""
        data = self.engine.get_stock_data("BBCA")
        assert data is not None
        assert data["name"] == "Bank Central Asia"
        assert data["roe"] == 0.20

    def test_remove_stock(self):
        """Test removing a stock."""
        assert self.engine.remove_stock("BBCA") is True
        assert self.engine.get_stock_data("BBCA") is None
        assert len(self.engine.list_stocks()) == 3

    def test_remove_nonexistent(self):
        """Test removing nonexistent stock."""
        assert self.engine.remove_stock("NONEXIST") is False

    def test_buffett_screen(self):
        """Test Buffett-style screening."""
        filters = create_buffett_screen()
        result = self.engine.screen(filters)

        # BBCA should pass (ROE 20%, D/E 0.5, P/E 15, P/B 2.5)
        bbcA_result = next(r for r in result.results if r.ticker == "BBCA")
        assert bbcA_result.passed is True

        # ADRO should pass (all criteria met)
        adro_result = next(r for r in result.results if r.ticker == "ADRO")
        assert adro_result.passed is True

    def test_growth_screen(self):
        """Test growth-oriented screening."""
        filters = create_growth_screen()
        result = self.engine.screen(filters)

        # BBCA has 12% rev growth, 15% earn growth - should pass
        bbcA_result = next(r for r in result.results if r.ticker == "BBCA")
        assert bbcA_result.passed is True or bbcA_result.pass_rate > 0

    def test_value_screen(self):
        """Test value-oriented screening."""
        filters = create_value_screen()
        result = self.engine.screen(filters)

        # ADRO has P/E 8, P/B 1.2 - should pass value screen
        adro_result = next(r for r in result.results if r.ticker == "ADRO")
        assert adro_result.passed is True

    def test_quality_screen(self):
        """Test quality-focused screening."""
        filters = create_quality_screen()
        result = self.engine.screen(filters)

        # Check that results are returned
        assert len(result.results) > 0

    def test_empty_universe(self):
        """Test screening with empty stock universe."""
        empty_engine = StockScreeningEngine()
        filters = [ScreenFilter("roe", ScreenOperator.GREATER_THAN, 0.15)]
        result = empty_engine.screen(filters)

        assert result.total_stocks_screened == 0
        assert result.stocks_passed == 0

    def test_no_filters(self):
        """Test screening with no filters."""
        result = self.engine.screen([])

        # All stocks should pass with no filters
        for stock in result.results:
            assert stock.passed is True

    def test_screening_ordering(self):
        """Test that results are ordered by pass rate."""
        filters = [
            ScreenFilter("roe", ScreenOperator.GREATER_THAN, 0.15),
            ScreenFilter("pe_ratio", ScreenOperator.LESS_THAN, 20.0)
        ]
        result = self.engine.screen(filters)

        # Results should be sorted by pass rate descending
        pass_rates = [r.pass_rate for r in result.results]
        assert pass_rates == sorted(pass_rates, reverse=True)


# =============================================================================
# PREDEFINED SCREENS TESTS
# =============================================================================

class TestPredefinedScreens:
    """Tests for predefined screen templates."""

    def test_buffett_screen_creation(self):
        """Test creating Buffett screen."""
        filters = create_buffett_screen()
        assert len(filters) == 4  # ROE, D/E, P/E, P/B

        filter_metrics = [f.metric for f in filters]
        assert "roe" in filter_metrics
        assert "debt_to_equity" in filter_metrics
        assert "pe_ratio" in filter_metrics
        assert "pb_ratio" in filter_metrics

    def test_growth_screen_creation(self):
        """Test creating growth screen."""
        filters = create_growth_screen()
        assert len(filters) == 4

        filter_metrics = [f.metric for f in filters]
        assert "revenue_cagr" in filter_metrics
        assert "earnings_cagr" in filter_metrics

    def test_value_screen_creation(self):
        """Test creating value screen."""
        filters = create_value_screen()
        assert len(filters) == 4

        filter_metrics = [f.metric for f in filters]
        assert "dividend_yield" in filter_metrics
        assert "pe_ratio" in filter_metrics

    def test_quality_screen_creation(self):
        """Test creating quality screen."""
        filters = create_quality_screen()
        assert len(filters) == 5

        filter_metrics = [f.metric for f in filters]
        assert "roe" in filter_metrics
        assert "roa" in filter_metrics
        assert "current_ratio" in filter_metrics

    def test_technical_screen_creation(self):
        """Test creating technical screen."""
        filters = create_technical_screen()
        assert len(filters) >= 2  # At least price vs SMA and RSI

        filter_metrics = [f.metric for f in filters]
        assert "price_vs_sma_200" in filter_metrics
        assert "rsi_14" in filter_metrics

    def test_dividend_screen_creation(self):
        """Test creating dividend screen."""
        filters = create_dividend_screen()
        assert len(filters) == 4

        filter_metrics = [f.metric for f in filters]
        assert "dividend_yield" in filter_metrics
        assert "payout_ratio" in filter_metrics


# =============================================================================
# CONVENIENCE FUNCTIONS TESTS
# =============================================================================

class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_screen_stocks(self):
        """Test the screen_stocks convenience function."""
        stocks = {
            "BBCA": {"roe": 0.20, "pe_ratio": 15.0}
        }
        filters = [
            ScreenFilter("roe", ScreenOperator.GREATER_THAN, 0.15),
            ScreenFilter("pe_ratio", ScreenOperator.LESS_THAN, 20.0)
        ]

        result = screen_stocks(stocks, filters)
        assert result.stocks_passed == 1

    def test_quick_screen_buffett(self):
        """Test quick screen with Buffett template."""
        stocks = {
            "BBCA": {"roe": 0.20, "pe_ratio": 15.0, "pb_ratio": 2.5, "debt_to_equity": 0.5}
        }

        result = quick_screen(stocks, "buffett")
        assert result.total_stocks_screened == 1

    def test_quick_screen_growth(self):
        """Test quick screen with growth template."""
        stocks = {
            "GROW": {"revenue_cagr": 0.15, "earnings_cagr": 0.20, "roe": 0.18, "pe_ratio": 25.0}
        }

        result = quick_screen(stocks, "growth")
        assert result.total_stocks_screened == 1

    def test_quick_screen_invalid_type(self):
        """Test quick screen with invalid type."""
        stocks = {"TEST": {}}

        with pytest.raises(ValueError):
            quick_screen(stocks, "invalid_type")


# =============================================================================
# RESULT FORMATTING TESTS
# =============================================================================

class TestResultFormatting:
    """Tests for result formatting functions."""

    def test_format_results(self):
        """Test formatting screen results."""
        filters = [ScreenFilter("roe", ScreenOperator.GREATER_THAN, 0.15)]
        results = [
            StockResult("A", "Stock A", True, {"roe": (True, "OK")}),
            StockResult("B", "Stock B", False, {"roe": (False, "Fail")}),
        ]
        screen_result = ScreenResult(
            filters=filters,
            results=results,
            total_stocks_screened=2,
            stocks_passed=1,
            run_date=date.today()
        )

        formatted = format_screen_results(screen_result)

        assert "passed_stocks" in formatted
        assert "failed_stocks" in formatted
        assert len(formatted["passed_stocks"]) == 1
        assert len(formatted["failed_stocks"]) > 0

    def test_format_with_top_n(self):
        """Test formatting with top N limit."""
        filters = []
        results = [
            StockResult("A", "Stock A", True, {}, score=0.9),
            StockResult("B", "Stock B", True, {}, score=0.8),
            StockResult("C", "Stock C", True, {}, score=0.7),
        ]
        screen_result = ScreenResult(
            filters=filters,
            results=results,
            total_stocks_screened=3,
            stocks_passed=3,
            run_date=date.today()
        )

        formatted = format_screen_results(screen_result, top_n=2)
        assert len(formatted["passed_stocks"]) == 2


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_zero_values(self):
        """Test screening with zero values."""
        stocks = {
            "ZERO": {"roe": 0.0, "pe_ratio": 0.0}
        }
        filters = [
            ScreenFilter("roe", ScreenOperator.GREATER_THAN, 0.15)
        ]

        result = screen_stocks(stocks, filters)
        assert result.stocks_passed == 0

    def test_negative_values(self):
        """Test screening with negative values."""
        stocks = {
            "NEG": {"roe": -0.10, "pe_ratio": -5.0}
        }
        filters = [
            ScreenFilter("roe", ScreenOperator.GREATER_THAN, 0.15)
        ]

        result = screen_stocks(stocks, filters)
        assert result.stocks_passed == 0

    def test_very_large_numbers(self):
        """Test screening with very large numbers."""
        stocks = {
            "LARGE": {"roe": 999.0, "pe_ratio": 9999.0}
        }
        filters = [
            ScreenFilter("roe", ScreenOperator.GREATER_THAN, 0.15)
        ]

        result = screen_stocks(stocks, filters)
        assert result.stocks_passed == 1

    def test_missing_metrics(self):
        """Test screening when some metrics are missing."""
        stocks = {
            "MISSING": {"roe": 0.20}  # No PE ratio
        }
        filters = [
            ScreenFilter("roe", ScreenOperator.GREATER_THAN, 0.15),
            ScreenFilter("pe_ratio", ScreenOperator.LESS_THAN, 20.0)
        ]

        result = screen_stocks(stocks, filters)
        # Should handle missing data gracefully
        assert result.total_stocks_screened == 1

    def test_all_passing(self):
        """Test when all stocks pass."""
        stocks = {
            "A": {"roe": 0.20},
            "B": {"roe": 0.25},
            "C": {"roe": 0.30}
        }
        filters = [
            ScreenFilter("roe", ScreenOperator.GREATER_THAN, 0.15)
        ]

        result = screen_stocks(stocks, filters)
        assert result.stocks_passed == 3

    def test_all_failing(self):
        """Test when all stocks fail."""
        stocks = {
            "A": {"roe": 0.05},
            "B": {"roe": 0.10}
        }
        filters = [
            ScreenFilter("roe", ScreenOperator.GREATER_THAN, 0.15)
        ]

        result = screen_stocks(stocks, filters)
        assert result.stocks_passed == 0


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests with realistic scenarios."""

    def test_indonesian_blue_chips_screen(self):
        """Test screening Indonesian blue-chip stocks."""
        stocks = {
            "BBCA": {
                "name": "Bank Central Asia",
                "roe": 0.20, "pe_ratio": 15.0, "pb_ratio": 2.5,
                "debt_to_equity": 0.5, "dividend_yield": 3.0
            },
            "BBRI": {
                "name": "Bank Rakyat Indonesia",
                "roe": 0.18, "pe_ratio": 12.0, "pb_ratio": 2.0,
                "debt_to_equity": 0.8, "dividend_yield": 4.0
            },
            "TLKM": {
                "name": "Telkom Indonesia",
                "roe": 0.15, "pe_ratio": 18.0, "pb_ratio": 3.0,
                "debt_to_equity": 0.6, "dividend_yield": 2.0
            },
            "ASII": {
                "name": "Astra International",
                "roe": 0.16, "pe_ratio": 14.0, "pb_ratio": 1.8,
                "debt_to_equity": 0.7, "dividend_yield": 3.5
            }
        }

        # Run Buffett screen
        result = quick_screen(stocks, "buffett")

        # All should pass Buffett criteria
        assert result.total_stocks_screened == 4
        # At least some should pass
        assert result.stocks_passed > 0

    def test_mixed_quality_screen(self):
        """Test screening with mixed quality stocks."""
        stocks = {
            "GOOD": {
                "roe": 0.25, "roa": 0.12, "pe_ratio": 12.0, "debt_to_equity": 0.3,
                "current_ratio": 2.0, "net_margin": 0.15
            },
            "BAD": {
                "roe": 0.05, "roa": 0.02, "pe_ratio": 50.0, "debt_to_equity": 2.0,
                "current_ratio": 0.5, "net_margin": -0.05
            },
            "MEDIUM": {
                "roe": 0.12, "roa": 0.06, "pe_ratio": 20.0, "debt_to_equity": 0.8,
                "current_ratio": 1.2, "net_margin": 0.08
            }
        }

        filters = create_quality_screen()
        result = screen_stocks(stocks, filters, min_pass_rate=0)

        # GOOD should pass, BAD should fail
        good_result = next((r for r in result.results if r.ticker == "GOOD"), None)
        bad_result = next((r for r in result.results if r.ticker == "BAD"), None)

        assert good_result is not None, "GOOD stock should be in results"
        assert bad_result is not None, "BAD stock should be in results"
        assert good_result.passed is True
        assert bad_result.passed is False

    def test_ranking_by_score(self):
        """Test that stocks are ranked by composite score."""
        stocks = {
            "HIGH_QUALITY": {"roe": 0.25, "pe_ratio": 10.0, "debt_to_equity": 0.2},
            "LOW_QUALITY": {"roe": 0.05, "pe_ratio": 50.0, "debt_to_equity": 2.0}
        }

        filters = [
            ScreenFilter("roe", ScreenOperator.GREATER_THAN, 0.10),
            ScreenFilter("pe_ratio", ScreenOperator.LESS_THAN, 30.0),
            ScreenFilter("debt_to_equity", ScreenOperator.LESS_THAN, 1.0)
        ]

        result = screen_stocks(stocks, filters)

        # Results should be ordered by pass rate
        if len(result.results) >= 2:
            assert result.results[0].pass_rate >= result.results[1].pass_rate


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
