"""
Tests for AI Tool Layer (Phase 10).

Tests cover:
- Tool function signatures and return types
- Structured data formatting
- Error handling for missing data
- Integration with existing analysis modules
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime
from typing import Dict, List

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.tools import (
    _format_metric_result,
    _format_structured_result,
    _safe_float,
    batch_compare,
    batch_screen,
    compare_stocks,
    get_company_news,
    get_financials,
    get_fundamental_analysis,
    get_historical_analysis,
    get_ownership,
    get_stock_price,
    get_technical_analysis,
    get_valuation,
    run_backtest,
    run_screening,
)
from models import FinancialMetrics

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_test_metrics(
    revenue: float = 10000.0,
    net_income: float = 1500.0,
    total_equity: float = 5000.0,
    total_assets: float = 20000.0,
    total_debt: float = 3000.0,
    gross_profit: float = 4000.0,
    operating_income: float = 2500.0,
    eps: float = 150.0,
) -> FinancialMetrics:
    """Create a test FinancialMetrics object."""
    return FinancialMetrics(
        revenue=revenue,
        net_income=net_income,
        total_equity=total_equity,
        total_assets=total_assets,
        total_debt=total_debt,
        gross_profit=gross_profit,
        operating_income=operating_income,
        eps=eps,
    )


# =============================================================================
# TESTS FOR HELPER FUNCTIONS
# =============================================================================

class TestHelperFunctions:
    """Tests for helper functions."""

    def test_safe_float_with_none(self):
        """Test _safe_float with None input."""
        assert _safe_float(None) is None

    def test_safe_float_with_valid_number(self):
        """Test _safe_float with valid number."""
        assert _safe_float(123.45) == 123.45

    def test_safe_float_with_string(self):
        """Test _safe_float with string number."""
        assert _safe_float("123.45") == 123.45

    def test_safe_float_with_invalid_string(self):
        """Test _safe_float with invalid string."""
        assert _safe_float("abc") is None

    def test_format_metric_result_with_none(self):
        """Test _format_metric_result with None."""
        result = _format_metric_result(None)
        assert result == {"value": None, "is_available": False}

    def test_format_metric_result_with_value(self):
        """Test _format_metric_result with a value."""
        result = _format_metric_result(0.15)
        assert result == {"value": 0.15, "is_available": True}

    def test_format_structured_result_with_dates(self):
        """Test _format_structured_result with date values."""
        test_date = date(2024, 1, 1)
        data = {"date": test_date, "value": 100}
        result = _format_structured_result(data)
        assert result["date"] == "2024-01-01"
        assert result["value"] == 100


# =============================================================================
# TESTS FOR CORE TOOLS
# =============================================================================

class TestCoreTools:
    """Tests for core tool functions."""

    def test_get_stock_price_returns_dict(self):
        """Test get_stock_price returns a dictionary."""
        result = get_stock_price("BBCA")
        assert isinstance(result, dict)
        assert result["ticker"] == "BBCA"
        assert "price" in result
        assert "as_of" in result

    def test_get_stock_price_with_different_source(self):
        """Test get_stock_price with different source."""
        result = get_stock_price("BBCA", source="idx")
        assert result["source"] == "idx"

    def test_get_financials_returns_dict(self):
        """Test get_financials returns a dictionary."""
        result = get_financials("BBCA")
        assert isinstance(result, dict)
        assert result["ticker"] == "BBCA"
        assert result["period"] == "latest"

    def test_get_financials_with_period(self):
        """Test get_financials with specific period."""
        result = get_financials("BBCA", period="annual")
        assert result["period"] == "annual"

    def test_get_fundamental_analysis_with_metrics(self):
        """Test get_fundamental_analysis with FinancialMetrics."""
        metrics = create_test_metrics()
        result = get_fundamental_analysis("BBCA", metrics)

        assert isinstance(result, dict)
        assert result["ticker"] == "BBCA"
        assert "growth" in result
        assert "profitability" in result
        assert "financial_health" in result
        assert "cash_flow" in result

    def test_get_fundamental_analysis_without_metrics(self):
        """Test get_fundamental_analysis without metrics."""
        result = get_fundamental_analysis("BBCA")
        assert "notes" in result
        assert "No financial data found" in result["notes"]

    def test_get_technical_analysis_with_prices(self):
        """Test get_technical_analysis with price data."""
        prices = [100 + i for i in range(50)]  # 50 days of prices
        result = get_technical_analysis("BBCA", prices=prices)

        assert isinstance(result, dict)
        assert result["ticker"] == "BBCA"
        assert "indicators" in result
        assert "signals" in result

    def test_get_technical_analysis_insufficient_data(self):
        """Test get_technical_analysis with insufficient data."""
        result = get_technical_analysis("BBCA", prices=[100, 101])
        assert "notes" in result
        assert "Insufficient price data" in result["notes"]

    def test_get_valuation_with_data(self):
        """Test get_valuation with complete data."""
        metrics = create_test_metrics()
        result = get_valuation("BBCA", price=8500, metrics=metrics)

        assert isinstance(result, dict)
        assert result["ticker"] == "BBCA"
        assert "valuations" in result

    def test_get_valuation_without_price(self):
        """Test get_valuation without price."""
        metrics = create_test_metrics()
        result = get_valuation("BBCA", metrics=metrics)
        assert "notes" in result

    def test_get_historical_analysis_with_data(self):
        """Test get_historical_analysis with raw data."""
        raw_data = [
            {"fsDate": "2023-12-31", "sales": 10000.0, "profitAttrOwner": 1000.0},
            {"fsDate": "2024-12-31", "sales": 12000.0, "profitAttrOwner": 1300.0},
        ]
        result = get_historical_analysis("BBCA", raw_data=raw_data)

        assert isinstance(result, dict)
        assert result["ticker"] == "BBCA"
        assert "growth" in result
        assert "trends" in result

    def test_get_historical_analysis_insufficient_data(self):
        """Test get_historical_analysis with insufficient data."""
        result = get_historical_analysis("BBCA", raw_data=[{"fsDate": "2024-12-31", "sales": 10000.0}])
        assert "notes" in result
        assert "Historical financial data not available" in result["notes"]

    def test_get_company_news(self):
        """Test get_company_news returns expected structure."""
        result = get_company_news("BBCA", limit=5)
        assert isinstance(result, dict)
        assert result["ticker"] == "BBCA"
        assert result["limit"] == 5
        assert result["count"] == 0

    def test_get_ownership(self):
        """Test get_ownership returns expected structure."""
        result = get_ownership("BBCA")
        assert isinstance(result, dict)
        assert result["ticker"] == "BBCA"
        assert "insiders" in result
        assert "major_shareholders" in result


# =============================================================================
# TESTS FOR SCREENING TOOLS
# =============================================================================

class TestScreeningTools:
    """Tests for screening tool functions."""

    def test_run_screening_with_no_stocks(self):
        """Test run_screening with no stocks."""
        result = run_screening()
        assert result["count"] == 0
        assert "No stocks provided" in result["notes"]

    def test_run_screening_with_empty_stocks(self):
        """Test run_screening with empty stocks dict."""
        result = run_screening(stocks={})
        assert result["count"] == 0

    def test_run_screening_with_filters(self):
        """Test run_screening with custom filters."""
        stocks = {
            "BBCA": {"roe": 0.25, "pe_ratio": 15.0, "debt_to_equity": 0.3},
            "BBRI": {"roe": 0.15, "pe_ratio": 12.0, "debt_to_equity": 0.5},
        }
        filters = [
            {"metric": "roe", "operator": ">=", "value": 0.15},
            {"metric": "pe_ratio", "operator": "<=", "value": 20.0},
        ]
        result = run_screening(stocks=stocks, filters=filters)

        assert isinstance(result, dict)
        assert "results" in result
        assert "count" in result

    def test_run_screening_with_screen_type(self):
        """Test run_screening with predefined screen type."""
        stocks = {
            "BBCA": {"roe": 0.25, "pe_ratio": 15.0, "debt_to_equity": 0.3,
                     "current_ratio": 2.0, "net_margin": 0.15},
            "BAD": {"roe": 0.05, "pe_ratio": 50.0, "debt_to_equity": 2.0,
                    "current_ratio": 0.5, "net_margin": -0.05},
        }
        result = run_screening(stocks=stocks, screen_type="buffett")

        assert isinstance(result, dict)
        assert "results" in result

    def test_run_screening_no_filters(self):
        """Test run_screening with no filters or screen type."""
        result = run_screening(stocks={"BBCA": {}})
        assert "notes" in result
        assert "No filters" in result["notes"]


# =============================================================================
# TESTS FOR COMPARISON TOOLS
# =============================================================================

class TestComparisonTools:
    """Tests for comparison tool functions."""

    def test_compare_stocks(self):
        """Test compare_stocks returns expected structure."""
        result = compare_stocks(["BBCA", "BBRI"])

        assert isinstance(result, dict)
        assert "tickers" in result
        assert "comparison_date" in result
        assert "stocks" in result
        assert len(result["tickers"]) == 2

    def test_batch_screen(self):
        """Test batch_screen returns expected structure."""
        result = batch_screen(["BBCA", "BBRI"], screen_type="buffett")

        assert isinstance(result, dict)
        assert "results" in result

    def test_batch_compare(self):
        """Test batch_compare returns expected structure."""
        result = batch_compare(["BBCA", "BBRI"])

        assert isinstance(result, dict)
        assert "tickers" in result


# =============================================================================
# TESTS FOR BACKTEST TOOL
# =============================================================================

class TestBacktestTool:
    """Tests for backtest tool function."""

    def test_run_backtest_without_data(self):
        """Test run_backtest without price data."""
        result = run_backtest("BBCA")

        assert isinstance(result, dict)
        assert result["ticker"] == "BBCA"
        # Should have error note since no price data
        assert "notes" in result or "error" in result


# =============================================================================
# TESTS FOR DATA FORMATTING
# =============================================================================

class TestDataFormatting:
    """Tests for data formatting and serialization."""

    def test_structured_result_formats_dates(self):
        """Test that dates are formatted as ISO strings."""
        from ai.tools import _format_structured_result

        data = {
            "date": date(2024, 1, 1),
            "datetime": datetime(2024, 1, 1, 12, 0),
            "nested": {"date": date(2024, 6, 30)},
            "list": [date(2024, 1, 1), date(2024, 12, 31)],
        }

        result = _format_structured_result(data)

        assert result["date"] == "2024-01-01"
        assert result["datetime"] == "2024-01-01T12:00:00"
        assert result["nested"]["date"] == "2024-06-30"
        assert result["list"][0] == "2024-01-01"

    def test_structured_result_preserves_numbers(self):
        """Test that numbers are preserved."""
        from ai.tools import _format_structured_result

        data = {"value": 123.45, "integer": 42, "negative": -10}
        result = _format_structured_result(data)

        assert result["value"] == 123.45
        assert result["integer"] == 42
        assert result["negative"] == -10

    def test_structured_result_preserves_strings(self):
        """Test that strings are preserved."""
        from ai.tools import _format_structured_result

        data = {"text": "Hello World", "ticker": "BBCA"}
        result = _format_structured_result(data)

        assert result["text"] == "Hello World"
        assert result["ticker"] == "BBCA"


# =============================================================================
# TESTS FOR ERROR HANDLING
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in tools."""

    def test_get_fundamental_analysis_invalid_metrics(self):
        """Test get_fundamental_analysis with invalid metrics type."""
        result = get_fundamental_analysis("BBCA", metrics="invalid")
        assert isinstance(result, dict)
        assert "notes" in result

    def test_get_technical_analysis_invalid_prices(self):
        """Test get_technical_analysis with invalid prices."""
        result = get_technical_analysis("BBCA", prices="not a list")
        assert isinstance(result, dict)
        assert "notes" in result

    def test_run_screening_invalid_filters(self):
        """Test run_screening with invalid filter format."""
        result = run_screening(stocks={"BBCA": {}}, filters="invalid")
        # Should handle gracefully
        assert isinstance(result, dict)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for AI tools."""

    def test_full_stock_profile_workflow(self):
        """Test getting a complete stock profile."""
        # Get fundamental analysis
        metrics = create_test_metrics()
        fundamentals = get_fundamental_analysis("BBCA", metrics)

        # Verify structure
        assert "growth" in fundamentals
        assert "profitability" in fundamentals
        assert "financial_health" in fundamentals

        # Check that metrics are properly formatted
        roe_result = fundamentals["profitability"].get("roe", {})
        assert "value" in roe_result
        assert "is_available" in roe_result

    def test_screening_workflow(self):
        """Test complete screening workflow."""
        stocks = {
            "BBCA": {
                "roe": 0.25,
                "roa": 0.12,
                "pe_ratio": 15.0,
                "debt_to_equity": 0.3,
                "current_ratio": 2.0,
                "net_margin": 0.15,
            },
            "BBRI": {
                "roe": 0.18,
                "roa": 0.09,
                "pe_ratio": 12.0,
                "debt_to_equity": 0.4,
                "current_ratio": 1.8,
                "net_margin": 0.12,
            },
            "BAD": {
                "roe": 0.05,
                "roa": 0.02,
                "pe_ratio": 50.0,
                "debt_to_equity": 2.0,
                "current_ratio": 0.5,
                "net_margin": -0.05,
            },
        }

        result = run_screening(stocks=stocks, screen_type="quality")

        assert result["count"] == 3
        assert "results" in result

        # Find results by ticker
        bbcA_result = next((r for r in result["results"] if r["ticker"] == "BBCA"), None)
        bad_result = next((r for r in result["results"] if r["ticker"] == "BAD"), None)

        assert bbcA_result is not None
        assert bad_result is not None
        assert bbcA_result["passed"] is True
        assert bad_result["passed"] is False

    def test_historical_analysis_workflow(self):
        """Test complete historical analysis workflow."""
        raw_data = [
            {"fsDate": "2022-12-31", "sales": 8000.0, "profitAttrOwner": 800.0},
            {"fsDate": "2023-12-31", "sales": 10000.0, "profitAttrOwner": 1000.0},
            {"fsDate": "2024-12-31", "sales": 12000.0, "profitAttrOwner": 1300.0},
        ]

        result = get_historical_analysis("BBCA", raw_data=raw_data)

        assert result["ticker"] == "BBCA"
        assert "growth" in result
        assert "trends" in result

        # Check that growth rates are calculated
        revenue_growth = result["growth"].get("revenue", {})
        assert "value" in revenue_growth
        assert "is_available" in revenue_growth


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
