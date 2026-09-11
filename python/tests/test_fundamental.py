"""
Tests for Fundamental Analysis Engine (Phase 2).

Tests all deterministic calculations for:
- Growth metrics (CAGR)
- Profitability ratios
- Financial health ratios
- Cash flow metrics
- Edge cases (missing data, division by zero, etc.)
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

from analysis.fundamental import (
    # MetricResult class
    MetricResult,
    _calculate_cagr,
    _ensure_positive,
    # Helper functions
    _safe_divide,
    # Batch calculations
    calculate_all_metrics,
    calculate_growth_metrics,
    current_ratio,
    # Financial health metrics
    debt_to_equity,
    earnings_cagr,
    eps_cagr,
    fcf_cagr,
    fcf_margin,
    # Cash flow metrics
    free_cash_flow,
    get_latest_ratios,
    # Profitability metrics
    gross_margin,
    interest_coverage,
    net_debt_to_ebitda,
    net_margin,
    operating_margin,
    # Growth metrics
    revenue_cagr,
    roa,
    roe,
    roic,
)
from models import FinancialMetrics

# =============================================================================
# HELPER FUNCTION TESTS
# =============================================================================

class TestSafeDivide:
    """Tests for _safe_divide helper."""

    def test_normal_division(self):
        assert _safe_divide(10.0, 2.0) == 5.0

    def test_division_by_zero_returns_none(self):
        assert _safe_divide(10.0, 0.0) is None

    def test_none_numerator(self):
        assert _safe_divide(None, 2.0) is None

    def test_none_denominator(self):
        assert _safe_divide(10.0, None) is None


class TestCalculateCagr:
    """Tests for CAGR calculation."""

    def test_normal_cagr(self):
        # 100 -> 150 in 2 years: (1.5)^(1/2) - 1 ≈ 0.2247
        result = _calculate_cagr(100.0, 150.0, 2)
        assert result is not None
        assert abs(result - 0.2247) < 0.001

    def test_zero_years(self):
        assert _calculate_cagr(100.0, 150.0, 0) is None

    def test_negative_years(self):
        assert _calculate_cagr(100.0, 150.0, -1) is None

    def test_zero_start_value(self):
        assert _calculate_cagr(0.0, 100.0, 2) is None

    def test_none_values(self):
        assert _calculate_cagr(None, 100.0, 2) is None
        assert _calculate_cagr(100.0, None, 2) is None

    def test_negative_end_value(self):
        # Can't calculate CAGR with negative values
        assert _calculate_cagr(100.0, -50.0, 2) is None


class TestEnsurePositive:
    """Tests for _ensure_positive helper."""

    def test_positive_value(self):
        assert _ensure_positive(10.0) == 10.0

    def test_zero_returns_none(self):
        assert _ensure_positive(0.0) is None

    def test_negative_returns_none(self):
        assert _ensure_positive(-5.0) is None

    def test_none_returns_none(self):
        assert _ensure_positive(None) is None


# =============================================================================
# GROWTH METRICS TESTS
# =============================================================================

class TestRevenueCagr:
    """Tests for revenue CAGR calculation."""

    def test_positive_growth(self):
        result = revenue_cagr(1000.0, 1500.0, 2)
        assert result.value is not None
        assert result.metric_name == "revenue_cagr"
        assert result.is_available

    def test_no_growth(self):
        result = revenue_cagr(1000.0, 1000.0, 2)
        assert result.value == 0.0

    def test_negative_growth(self):
        result = revenue_cagr(1000.0, 800.0, 2)
        assert result.value is not None
        assert result.value < 0

    def test_missing_start_value(self):
        result = revenue_cagr(None, 1000.0, 2)
        assert result.value is None
        assert not result.is_available

    def test_missing_end_value(self):
        result = revenue_cagr(1000.0, None, 2)
        assert result.value is None

    def test_zero_years(self):
        result = revenue_cagr(1000.0, 1500.0, 0)
        assert result.value is None


class TestEarningsCagr:
    """Tests for earnings CAGR calculation."""

    def test_normal_calculation(self):
        result = earnings_cagr(100.0, 150.0, 3)
        assert result.value is not None
        assert result.metric_name == "earnings_cagr"

    def test_negative_earnings(self):
        # Loss to smaller loss
        result = earnings_cagr(-100.0, -50.0, 2)
        assert result.value is None  # Negative start value


class TestEpsCagr:
    """Tests for EPS CAGR calculation."""

    def test_positive_eps_growth(self):
        result = eps_cagr(100.0, 150.0, 2)
        assert result.value is not None

    def test_missing_eps(self):
        result = eps_cagr(None, 150.0, 2)
        assert result.value is None


class TestFcfCagr:
    """Tests for FCF CAGR calculation."""

    def test_positive_fcf_growth(self):
        result = fcf_cagr(500.0, 750.0, 3)
        assert result.value is not None

    def test_zero_fcf_start(self):
        result = fcf_cagr(0.0, 500.0, 2)
        assert result.value is None


# =============================================================================
# PROFITABILITY METRICS TESTS
# =============================================================================

class TestGrossMargin:
    """Tests for gross margin calculation."""

    def test_normal_margin(self):
        # 4500 / 10000 = 0.45
        result = gross_margin(4500.0, 10000.0)
        assert result.value == 0.45
        assert result.metric_name == "gross_margin"

    def test_high_margin(self):
        result = gross_margin(9000.0, 10000.0)
        assert result.value == 0.9

    def test_low_margin(self):
        result = gross_margin(1000.0, 10000.0)
        assert result.value == 0.1

    def test_missing_revenue(self):
        result = gross_margin(4500.0, None)
        assert result.value is None

    def test_zero_revenue(self):
        result = gross_margin(4500.0, 0.0)
        assert result.value is None

    def test_missing_gross_profit(self):
        result = gross_margin(None, 10000.0)
        assert result.value is None


class TestOperatingMargin:
    """Tests for operating margin calculation."""

    def test_normal_margin(self):
        result = operating_margin(2000.0, 10000.0)
        assert result.value == 0.2

    def test_negative_operating_income(self):
        # Operating loss
        result = operating_margin(-1000.0, 10000.0)
        assert result.value == -0.1  # Negative margin is valid

    def test_missing_values(self):
        assert operating_margin(None, 10000.0).value is None
        assert operating_margin(2000.0, None).value is None


class TestNetMargin:
    """Tests for net margin calculation."""

    def test_normal_margin(self):
        result = net_margin(1500.0, 10000.0)
        assert result.value == 0.15

    def test_loss(self):
        result = net_margin(-500.0, 10000.0)
        assert result.value == -0.05

    def test_zero_revenue(self):
        result = net_margin(1000.0, 0.0)
        assert result.value is None


class TestRoe:
    """Tests for Return on Equity calculation."""

    def test_normal_roe(self):
        # 1500 / 10000 = 0.15 = 15%
        result = roe(1500.0, 10000.0)
        assert result.value == 0.15

    def test_high_roe(self):
        # 3000 / 10000 = 0.30 = 30%
        result = roe(3000.0, 10000.0)
        assert result.value == 0.30

    def test_zero_equity(self):
        result = roe(1500.0, 0.0)
        assert result.value is None

    def test_negative_equity(self):
        # Negative equity - unusual but should handle gracefully
        result = roe(1500.0, -10000.0)
        assert result.value is None

    def test_missing_net_income(self):
        result = roe(None, 10000.0)
        assert result.value is None


class TestRoa:
    """Tests for Return on Assets calculation."""

    def test_normal_roa(self):
        # 1000 / 20000 = 0.05 = 5%
        result = roa(1000.0, 20000.0)
        assert result.value == 0.05

    def test_zero_assets(self):
        result = roa(1000.0, 0.0)
        assert result.value is None


class TestRoic:
    """Tests for Return on Invested Capital calculation."""

    def test_normal_roic(self):
        # Net Income / (Equity + Debt) = 1500 / (10000 + 5000) = 0.1
        result = roic(1500.0, 10000.0, 5000.0)
        assert result.value == 0.1

    def test_zero_capital(self):
        result = roic(1500.0, 0.0, 0.0)
        assert result.value is None

    def test_negative_equity(self):
        # Should return None when capital is negative
        result = roic(1500.0, -5000.0, 10000.0)
        assert result.value is None


# =============================================================================
# FINANCIAL HEALTH METRICS TESTS
# =============================================================================

class TestDebtToEquity:
    """Tests for Debt-to-Equity ratio."""

    def test_normal_ratio(self):
        # 5000 / 10000 = 0.5
        result = debt_to_equity(5000.0, 10000.0)
        assert result.value == 0.5

    def test_high_leverage(self):
        # 15000 / 10000 = 1.5
        result = debt_to_equity(15000.0, 10000.0)
        assert result.value == 1.5

    def test_zero_equity(self):
        result = debt_to_equity(5000.0, 0.0)
        assert result.value is None

    def test_no_debt(self):
        result = debt_to_equity(0.0, 10000.0)
        assert result.value == 0.0

    def test_missing_equity(self):
        result = debt_to_equity(5000.0, None)
        assert result.value is None


class TestNetDebtToEbitda:
    """Tests for Net Debt to EBITDA ratio."""

    def test_normal_ratio(self):
        # Net Debt = 8000 - 2000 = 6000; 6000 / 2000 = 3.0
        result = net_debt_to_ebitda(8000.0, 2000.0, 2000.0)
        assert result.value == 3.0

    def test_negative_net_debt(self):
        # More cash than debt
        result = net_debt_to_ebitda(5000.0, 8000.0, 2000.0)
        assert result.value == -1.5  # Negative net debt

    def test_zero_ebitda(self):
        result = net_debt_to_ebitda(5000.0, 2000.0, 0.0)
        assert result.value is None

    def test_missing_values(self):
        assert net_debt_to_ebitda(None, 2000.0, 2000.0).value is None
        assert net_debt_to_ebitda(5000.0, None, 2000.0).value is None
        assert net_debt_to_ebitda(5000.0, 2000.0, None).value is None


class TestCurrentRatio:
    """Tests for Current Ratio."""

    def test_healthy_ratio(self):
        # 20000 / 10000 = 2.0
        result = current_ratio(20000.0, 10000.0)
        assert result.value == 2.0

    def test_low_ratio(self):
        # 8000 / 10000 = 0.8
        result = current_ratio(8000.0, 10000.0)
        assert result.value == 0.8

    def test_zero_liabilities(self):
        result = current_ratio(20000.0, 0.0)
        assert result.value is None

    def test_missing_values(self):
        assert current_ratio(None, 10000.0).value is None
        assert current_ratio(20000.0, None).value is None


class TestInterestCoverage:
    """Tests for Interest Coverage ratio."""

    def test_healthy_coverage(self):
        # 5000 / 1000 = 5.0
        result = interest_coverage(5000.0, 1000.0)
        assert result.value == 5.0

    def test_low_coverage(self):
        # 800 / 1000 = 0.8 (might struggle to pay interest)
        result = interest_coverage(800.0, 1000.0)
        assert result.value == 0.8

    def test_zero_interest(self):
        result = interest_coverage(5000.0, 0.0)
        assert result.value is None

    def test_missing_values(self):
        assert interest_coverage(None, 1000.0).value is None
        assert interest_coverage(5000.0, None).value is None


# =============================================================================
# CASH FLOW METRICS TESTS
# =============================================================================

class TestFreeCashFlow:
    """Tests for Free Cash Flow calculation."""

    def test_positive_fcf(self):
        # 3000 - 1000 = 2000
        result = free_cash_flow(3000.0, 1000.0)
        assert result.value == 2000.0

    def test_negative_fcf(self):
        # 1000 - 2000 = -1000
        result = free_cash_flow(1000.0, 2000.0)
        assert result.value == -1000.0

    def test_zero_capex(self):
        result = free_cash_flow(3000.0, 0.0)
        assert result.value == 3000.0

    def test_missing_values(self):
        assert free_cash_flow(None, 1000.0).value is None
        assert free_cash_flow(3000.0, None).value is None


class TestFcfMargin:
    """Tests for FCF Margin calculation."""

    def test_normal_margin(self):
        # 2000 / 10000 = 0.2
        result = fcf_margin(2000.0, 10000.0)
        assert result.value == 0.2

    def test_negative_fcf(self):
        # -1000 / 10000 = -0.1
        result = fcf_margin(-1000.0, 10000.0)
        assert result.value == -0.1

    def test_zero_revenue(self):
        result = fcf_margin(2000.0, 0.0)
        assert result.value is None

    def test_missing_values(self):
        assert fcf_margin(None, 10000.0).value is None
        assert fcf_margin(2000.0, None).value is None


# =============================================================================
# BATCH CALCULATION TESTS
# =============================================================================

class TestCalculateAllMetrics:
    """Tests for calculate_all_metrics function."""

    def test_complete_metrics(self):
        metrics = FinancialMetrics(
            revenue=10000.0,
            gross_profit=4500.0,
            operating_income=2000.0,
            net_income=1500.0,
            total_assets=20000.0,
            total_equity=10000.0,
            total_debt=5000.0,
            current_assets=8000.0,
            current_liabilities=4000.0,
            cash_and_equivalents=2000.0,
            operating_cash_flow=3000.0,
            capital_expenditures=1000.0,
            interest_expense=500.0
        )

        results = calculate_all_metrics(metrics, "2024")

        # Check some key metrics
        assert results["gross_margin"].value == 0.45
        assert results["net_margin"].value == 0.15
        assert results["roe"].value == 0.15
        assert results["roa"].value == 0.075
        assert results["debt_to_equity"].value == 0.5
        assert results["current_ratio"].value == 2.0
        assert results["free_cash_flow"].value == 2000.0

    def test_incomplete_metrics(self):
        metrics = FinancialMetrics(revenue=10000.0)  # Only revenue

        results = calculate_all_metrics(metrics, "2024")

        # All ratios should be None since other data is missing
        for key, result in results.items():
            if key in ("gross_margin", "operating_margin", "net_margin"):
                assert result.value is None or not result.is_available

    def test_stored_debt_to_equity_preferred_over_recompute(self):
        """A stored D/E is used when raw total_debt is missing.

        The DB stores the ratio directly while total_debt is often NULL, so
        recomputing from components would wrongly drop a known value.
        """
        metrics = FinancialMetrics(
            revenue=10000.0,
            net_income=1500.0,
            total_equity=10000.0,
            total_debt=None,          # raw component missing
            debt_to_equity=0.18,      # stored ratio present
        )

        results = calculate_all_metrics(metrics, "2024")

        assert results["debt_to_equity"].value == 0.18
        assert results["debt_to_equity"].is_available

    def test_recomputed_debt_to_equity_when_not_stored(self):
        """D/E falls back to total_debt/total_equity when nothing is stored."""
        metrics = FinancialMetrics(
            net_income=1500.0,
            total_equity=10000.0,
            total_debt=2500.0,
        )

        results = calculate_all_metrics(metrics, "2024")

        assert results["debt_to_equity"].value == 0.25

    def test_stored_roe_and_roa_preferred_over_recompute(self):
        """Stored ROE/ROA (official IDX figures) win over recomputation.

        The components imply 0.15/0.075, but the stored ratios are authoritative
        and must be surfaced so the report matches the published figure.
        """
        metrics = FinancialMetrics(
            revenue=10000.0,
            net_income=1500.0,
            total_assets=20000.0,
            total_equity=10000.0,
            roe=0.185,
            roa=0.084,
        )

        results = calculate_all_metrics(metrics, "2024")

        assert results["roe"].value == 0.185
        assert results["roa"].value == 0.084
        assert results["roe"].is_available
        assert results["roa"].is_available

    def test_roe_and_roa_recomputed_when_not_stored(self):
        """ROE/ROA fall back to components when no stored ratio exists."""
        metrics = FinancialMetrics(
            net_income=1500.0,
            total_assets=20000.0,
            total_equity=10000.0,
        )

        results = calculate_all_metrics(metrics, "2024")

        assert results["roe"].value == 0.15
        assert results["roa"].value == 0.075

    def test_exposes_component_roe_roa_beside_stored(self):
        """The component-derived ROE/ROA is exposed next to the stored one.

        Both bases stay visible so a reader can reconcile them instead of
        assuming the headline value is the only truth.
        """
        metrics = FinancialMetrics(
            revenue=10000.0,
            net_income=1500.0,
            total_assets=20000.0,
            total_equity=10000.0,
            roe=0.185,
            roa=0.084,
        )

        results = calculate_all_metrics(metrics, "2024")

        assert results["roe"].value == 0.185           # stored (data source)
        assert results["roe_components"].value == 0.15  # 1500 / 10000
        assert results["roa"].value == 0.084            # stored (data source)
        assert results["roa_components"].value == 0.075  # 1500 / 20000

    def test_component_companions_match_when_nothing_stored(self):
        """Without a stored ratio the companion equals the headline metric."""
        metrics = FinancialMetrics(
            net_income=1500.0,
            total_assets=20000.0,
            total_equity=10000.0,
        )

        results = calculate_all_metrics(metrics, "2024")

        assert results["roe"].value == results["roe_components"].value == 0.15
        assert results["roa"].value == results["roa_components"].value == 0.075

    def test_exposes_component_margins_beside_stored(self):
        """Stored margins are preferred and the component value is exposed too."""
        metrics = FinancialMetrics(
            revenue=10000.0,
            gross_profit=4000.0,      # component gross margin 0.40
            operating_income=1500.0,  # component operating margin 0.15
            net_income=1200.0,        # component net margin 0.12
            gross_margin=0.42,
            operating_margin=0.17,
            net_margin=0.15,
        )

        results = calculate_all_metrics(metrics, "2024")

        assert results["gross_margin"].value == 0.42
        assert results["gross_margin_components"].value == 0.40
        assert results["operating_margin"].value == 0.17
        assert results["operating_margin_components"].value == 0.15
        assert results["net_margin"].value == 0.15
        assert results["net_margin_components"].value == 0.12

    def test_margin_components_match_when_nothing_stored(self):
        """Margin companions equal the headline metric when nothing is stored."""
        metrics = FinancialMetrics(
            revenue=10000.0,
            gross_profit=4000.0,
            operating_income=1500.0,
            net_income=1200.0,
        )

        results = calculate_all_metrics(metrics, "2024")

        assert results["gross_margin"].value == results["gross_margin_components"].value == 0.40
        assert results["net_margin"].value == results["net_margin_components"].value == 0.12

    def test_exposes_component_roic_beside_stored(self):
        """Stored ROIC is preferred and the component value is exposed too."""
        metrics = FinancialMetrics(
            net_income=1200.0,
            total_equity=8000.0,
            total_debt=2000.0,  # component ROIC = 1200 / 10000 = 0.12
            roic=0.10,
        )

        results = calculate_all_metrics(metrics, "2024")

        assert results["roic"].value == 0.10
        assert results["roic_components"].value == 0.12

    def test_stored_roic_used_when_total_debt_missing(self):
        """A stored ROIC survives when the recomputation cannot run.

        Without ``total_debt`` the component calculation is unavailable, so the
        stored figure must still be surfaced (and the companion reports None).
        """
        metrics = FinancialMetrics(
            net_income=1200.0,
            total_equity=8000.0,
            total_debt=None,
            roic=0.11,
        )

        results = calculate_all_metrics(metrics, "2024")

        assert results["roic"].value == 0.11
        assert results["roic_components"].value is None


class TestCalculateGrowthMetrics:
    """Tests for growth metrics calculation."""

    def test_positive_growth(self):
        prev = FinancialMetrics(revenue=10000.0, net_income=1500.0, eps=150.0)
        curr = FinancialMetrics(revenue=12000.0, net_income=1800.0, eps=180.0)

        results = calculate_growth_metrics(prev, curr, years_apart=2)

        # Revenue grew from 10000 to 12000 in 2 years
        assert results["revenue_cagr"].value is not None
        assert results["revenue_cagr"].value > 0

        # Earnings grew from 1500 to 1800
        assert results["earnings_cagr"].value is not None

    def test_missing_data_in_comparison(self):
        prev = FinancialMetrics(revenue=10000.0)
        curr = FinancialMetrics()  # Empty

        results = calculate_growth_metrics(prev, curr, years_apart=1)

        # Growth metrics should handle missing data
        assert results["revenue_cagr"].value is None


class TestGetLatestRatios:
    """Tests for extracting pre-calculated ratios."""

    def test_with_precomputed_ratios(self):
        metrics = FinancialMetrics(
            revenue=10000.0,
            net_income=1500.0,
            roe=0.15,
            roa=0.075,
            debt_to_equity=0.5,
            pe_ratio=12.5,
            pb_ratio=2.0,
            net_margin=0.15
        )

        ratios = get_latest_ratios(metrics)

        assert ratios["roe"] == 0.15
        assert ratios["roa"] == 0.075
        assert ratios["debt_to_equity"] == 0.5
        assert ratios["pe_ratio"] == 12.5
        assert ratios["pb_ratio"] == 2.0

    def test_without_precomputed_ratios(self):
        metrics = FinancialMetrics(revenue=10000.0, net_income=1500.0)

        ratios = get_latest_ratios(metrics)

        # Should return empty dict or dict with only calculated values
        assert len(ratios) == 0


# =============================================================================
# METRIC RESULT TESTS
# =============================================================================

class TestMetricResult:
    """Tests for MetricResult dataclass."""

    def test_available_metric(self):
        result = MetricResult(value=0.15, metric_name="roe")
        assert result.is_available
        assert "0.1500" in repr(result)

    def test_unavailable_metric(self):
        result = MetricResult(value=None, metric_name="roe")
        assert not result.is_available
        assert "N/A" in repr(result)

    def test_with_period(self):
        result = MetricResult(value=0.15, metric_name="roe", period="2024")
        assert result.period == "2024"


# =============================================================================
# INTEGRATION TESTS WITH REAL DATA
# =============================================================================

class TestWithRealisticData:
    """Integration tests using realistic Indonesian stock data patterns."""

    def test_banka_bca_like_profile(self):
        """Test with BBCA-like financial profile."""
        metrics = FinancialMetrics(
            revenue=50000.0,  # 50 trillion IDR
            net_income=15000.0,
            total_assets=500000.0,
            total_equity=80000.0,
            total_debt=420000.0,
            current_assets=100000.0,
            current_liabilities=80000.0,
            cash_and_equivalents=30000.0,
            operating_income=18000.0,
            interest_expense=5000.0,
            operating_cash_flow=20000.0,
            capital_expenditures=2000.0
        )

        results = calculate_all_metrics(metrics, "2024")

        # Expected calculations:
        # Net margin = 15000/50000 = 0.30
        assert results["net_margin"].value == pytest.approx(0.30, abs=0.01)

        # ROE = 15000/80000 = 0.1875
        assert results["roe"].value == pytest.approx(0.1875, abs=0.01)

        # ROA = 15000/500000 = 0.03
        assert results["roa"].value == pytest.approx(0.03, abs=0.01)

        # D/E = 420000/80000 = 5.25
        assert results["debt_to_equity"].value == pytest.approx(5.25, abs=0.01)

        # Current ratio = 100000/80000 = 1.25
        assert results["current_ratio"].value == pytest.approx(1.25, abs=0.01)

        # Interest coverage = 18000/5000 = 3.6
        assert results["interest_coverage"].value == pytest.approx(3.6, abs=0.01)

        # FCF = 20000 - 2000 = 18000
        assert results["free_cash_flow"].value == 18000.0

    def test_cagr_over_multiple_years(self):
        """Test CAGR calculations over multiple periods."""
        # Simulate 5 years of data
        revenues = [10000, 11000, 12100, 13310, 14641]  # 10% CAGR
        earnings = [1000, 1100, 1210, 1331, 1464]

        prev = FinancialMetrics(revenue=revenues[0], net_income=earnings[0])
        curr = FinancialMetrics(revenue=revenues[-1], net_income=earnings[-1])

        results = calculate_growth_metrics(prev, curr, years_apart=4)

        # Revenue CAGR should be approximately 10%
        assert results["revenue_cagr"].value is not None
        assert abs(results["revenue_cagr"].value - 0.10) < 0.01

        # Earnings CAGR should be approximately 10%
        assert results["earnings_cagr"].value is not None
        assert abs(results["earnings_cagr"].value - 0.10) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
