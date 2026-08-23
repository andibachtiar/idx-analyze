"""
Tests for Stock Valuation Prompt Integration (Phase 16).

Tests cover:
- WACC calculation
- P/E and P/B valuation methods
- Prompt generation
- Full valuation analysis workflow
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.prompts.valuation import (
    ValuationResult,
    WACCCalculation,
    analyze_stock_valuation,
    calculate_pb_multiple,
    calculate_pe_multiple,
    calculate_wacc,
    generate_valuation_prompt,
)
from models import FinancialMetrics

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_metrics():
    """Create sample financial metrics for testing."""
    return FinancialMetrics(
        revenue=10000.0,
        net_income=1500.0,
        total_equity=5000.0,
        total_assets=20000.0,
        total_debt=3000.0,
        eps=150.0,
        shares_outstanding=1000000.0,
        roe=0.25,
        roa=0.12,
        debt_to_equity=0.3,
        revenue_cagr_3y=0.10,
    )


@pytest.fixture
def sample_wacc():
    """Create sample WACC calculation."""
    return WACCCalculation(
        risk_free_rate=0.06,
        beta=1.0,
        equity_risk_premium=0.05,
        size_premium=0.0,
        cost_of_equity=0.11,
        interest_expense=120.0,
        total_debt=3000.0,
        pre_tax_cost_of_debt=0.08,
        effective_tax_rate=0.25,
        after_tax_cost_of_debt=0.06,
        equity_weight=0.75,
        debt_weight=0.25,
        wacc=0.0975,
    )


# =============================================================================
# TESTS FOR WACC CALCULATION
# =============================================================================

class TestWACCCalculation:
    """Tests for WACC calculation."""

    def test_basic_wacc(self):
        """Test basic WACC calculation."""
        wacc = calculate_wacc()

        assert wacc.risk_free_rate == 0.06
        assert wacc.beta == 1.0
        assert wacc.wacc > 0
        assert wacc.wacc < 0.20  # Should be reasonable

    def test_high_debt_wacc(self):
        """Test WACC with high debt."""
        wacc = calculate_wacc(
            total_debt=8000.0,
            total_equity=2000.0,
            pre_tax_cost_of_debt=0.10,
        )

        assert wacc.debt_weight == 0.8
        assert wacc.equity_weight == 0.2

    def test_wacc_components(self):
        """Test WACC component calculations."""
        wacc = calculate_wacc()

        assert wacc.cost_of_equity == 0.11  # 0.06 + 1.0*0.05
        assert wacc.after_tax_cost_of_debt == 0.06  # 0.08 * (1 - 0.25)


# =============================================================================
# TESTS FOR VALUATION METHODS
# =============================================================================

class TestValuationMethods:
    """Tests for valuation methods."""

    def test_pe_multiple_positive_eps(self, sample_metrics):
        """Test P/E multiple with positive EPS."""
        result = calculate_pe_multiple(
            eps=sample_metrics.eps,
            peer_median_pe=15.0,
            growth_rate=0.10,
        )

        assert result.method_name == "P/E Multiple"
        assert result.base_value is not None
        assert result.bear_value < result.base_value
        assert result.bull_value > result.base_value
        assert result.confidence in ["HIGH", "MEDIUM", "LOW"]

    def test_pe_multiple_negative_eps(self):
        """Test P/E multiple with negative EPS."""
        result = calculate_pe_multiple(
            eps=-5.0,
            peer_median_pe=15.0,
            growth_rate=0.10,
        )

        assert result.bear_value is None
        assert result.base_value is None
        assert result.bull_value is None
        assert result.confidence == "LOW"

    def test_pb_multiple(self, sample_metrics):
        """Test P/B multiple calculation."""
        bvps = sample_metrics.total_equity / sample_metrics.shares_outstanding
        result = calculate_pb_multiple(
            book_value_per_share=bvps,
            roe=sample_metrics.roe,
            cost_of_equity=0.11,
        )

        assert result.method_name == "P/B Multiple"
        assert result.base_value is not None
        assert result.bear_value < result.base_value
        assert result.bull_value > result.base_value


# =============================================================================
# TESTS FOR PROMPT GENERATION
# =============================================================================

class TestPromptGeneration:
    """Tests for prompt generation."""

    def test_generate_valuation_prompt(self, sample_metrics, sample_wacc):
        """Test generating valuation prompt."""
        prompt = generate_valuation_prompt(
            ticker="BBCA",
            current_price=8500.0,
            metrics=sample_metrics,
            wacc_calc=sample_wacc,
        )

        assert isinstance(prompt, str)
        assert "BBCA" in prompt
        assert "Current Price" in prompt
        assert "P/E" in prompt
        assert "WACC" in prompt
        assert "Football Field" in prompt or "valuation" in prompt.lower()


# =============================================================================
# TESTS FOR FULL ANALYSIS
# =============================================================================

class TestFullAnalysis:
    """Tests for full valuation analysis."""

    def test_analyze_stock_valuation(self, sample_metrics):
        """Test complete valuation analysis."""
        result = analyze_stock_valuation(
            ticker="BBCA",
            current_price=8500.0,
            metrics=sample_metrics,
            peer_pe_median=15.0,
        )

        assert result["ticker"] == "BBCA"
        assert "analysis_date" in result
        assert "current_price" in result
        assert "wacc" in result
        assert "methods" in result
        assert "pe_multiple" in result["methods"]
        assert "pb_multiple" in result["methods"]

    def test_analyze_with_custom_wacc(self, sample_metrics, sample_wacc):
        """Test analysis with custom WACC."""
        result = analyze_stock_valuation(
            ticker="BBCA",
            current_price=8500.0,
            metrics=sample_metrics,
            wacc=sample_wacc,
        )

        assert result["wacc"]["wacc"] == sample_wacc.wacc

    def test_margin_of_safety(self, sample_metrics):
        """Test margin of safety calculation."""
        result = analyze_stock_valuation(
            ticker="BBCA",
            current_price=8500.0,
            metrics=sample_metrics,
            peer_pe_median=15.0,
        )

        assert "margin_of_safety" in result

    def test_without_llm(self, sample_metrics):
        """Test analysis without LLM."""
        result = analyze_stock_valuation(
            ticker="BBCA",
            current_price=8500.0,
            metrics=sample_metrics,
            use_llm=False,
        )

        assert "llm_used" not in result or result.get("llm_used") is False


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests."""

    def test_end_to_end_valuation(self, sample_metrics):
        """Test complete valuation workflow."""
        # Calculate WACC
        wacc = calculate_wacc(
            total_debt=sample_metrics.total_debt or 0,
            total_equity=sample_metrics.total_equity or 1000,
        )

        # Calculate valuations
        pe_result = calculate_pe_multiple(
            eps=sample_metrics.eps or 0,
            peer_median_pe=15.0,
            growth_rate=sample_metrics.revenue_cagr_3y or 0.10,
        )

        pb_result = calculate_pb_multiple(
            book_value_per_share=(sample_metrics.total_equity / (sample_metrics.shares_outstanding or 1)),
            roe=sample_metrics.roe or 0.10,
            cost_of_equity=wacc.cost_of_equity,
        )

        # Verify results
        assert pe_result.base_value is not None
        assert pb_result.base_value is not None

        # Full analysis
        result = analyze_stock_valuation(
            ticker="TEST",
            current_price=100.0,
            metrics=sample_metrics,
        )

        assert result["ticker"] == "TEST"
        assert "methods" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
