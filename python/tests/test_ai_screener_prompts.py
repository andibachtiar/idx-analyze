"""
Tests for Stock Screener Prompt Integration (Phase 18).

Tests cover:
- 5-factor scoring system
- Screening result generation
- Prompt generation
- Edge cases and error handling
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.prompts.screener import (
    FactorScore,
    StockScreenResult,
    calculate_growth_score,
    calculate_momentum_score,
    calculate_quality_score,
    calculate_sentiment_score,
    calculate_valuation_score,
    generate_screener_prompt,
    screen_stocks_with_scoring,
)

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_stock_data():
    """Create sample stock data for testing."""
    return [
        {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "pe_ratio": 25.0,
            "ps_ratio": 5.0,
            "ev_ebitda": 18.0,
            "peg_ratio": 1.5,
            "roe": 0.15,
            "roic": 0.12,
            "debt_to_equity": 0.5,
            "gross_margin": 0.40,
            "gross_margin_trend": 0.02,
            "revenue_growth_yoy": 0.08,
            "eps_growth_yoy": 0.10,
            "forward_revenue_growth": 0.07,
            "guidance_trend": "raised",
        },
        {
            "ticker": "MSFT",
            "name": "Microsoft Corporation",
            "pe_ratio": 30.0,
            "ps_ratio": 10.0,
            "ev_ebitda": 22.0,
            "peg_ratio": 2.0,
            "roe": 0.40,
            "roic": 0.30,
            "debt_to_equity": 0.3,
            "gross_margin": 0.68,
            "gross_margin_trend": 0.01,
            "revenue_growth_yoy": 0.12,
            "eps_growth_yoy": 0.15,
            "forward_revenue_growth": 0.10,
            "guidance_trend": "maintained",
        },
        {
            "ticker": "GOOGL",
            "name": "Alphabet Inc.",
            "pe_ratio": 20.0,
            "ps_ratio": 4.0,
            "ev_ebitda": 12.0,
            "peg_ratio": 1.0,
            "roe": 0.25,
            "roic": 0.20,
            "debt_to_equity": 0.1,
            "gross_margin": 0.55,
            "gross_margin_trend": 0.03,
            "revenue_growth_yoy": 0.10,
            "eps_growth_yoy": 0.12,
            "forward_revenue_growth": 0.09,
            "guidance_trend": "raised",
        },
    ]


@pytest.fixture
def sample_prices():
    """Create sample prices for technical scoring."""
    return {
        "AAPL": 150.0,
        "MSFT": 300.0,
        "GOOGL": 120.0,
    }


@pytest.fixture
def sample_technicals():
    """Create sample technical data."""
    return {
        "AAPL": {
            "sma_50": {"value": 145.0},
            "sma_200": {"value": 140.0},
            "rsi_14": {"value": 65.0},
        },
        "MSFT": {
            "sma_50": {"value": 295.0},
            "sma_200": {"value": 280.0},
            "rsi_14": {"value": 55.0},
        },
        "GOOGL": {
            "sma_50": {"value": 118.0},
            "sma_200": {"value": 115.0},
            "rsi_14": {"value": 70.0},
        },
    }


# =============================================================================
# TESTS FOR SCORING FUNCTIONS
# =============================================================================

class TestValuationScoring:
    """Tests for valuation score calculation."""

    def test_good_valuation(self):
        """Test scoring for reasonably valued stock."""
        result = calculate_valuation_score(
            pe_ratio=15.0,
            ps_ratio=2.0,
            ev_ebitda=10.0,
            peg_ratio=1.0,
        )

        assert isinstance(result, FactorScore)
        assert result.name == "Valuation"
        assert 0 <= result.score <= 10
        assert "P/E" in result.sub_scores
        assert "P/S" in result.sub_scores

    def test_expensive_valuation(self):
        """Test scoring for expensive stock."""
        result = calculate_valuation_score(
            pe_ratio=50.0,
            ps_ratio=15.0,
            ev_ebitda=35.0,
            peg_ratio=2.5,
        )

        assert result.score < 5  # Should be low score for expensive stock

    def test_missing_data(self):
        """Test scoring with missing data."""
        result = calculate_valuation_score(
            pe_ratio=None,
            ps_ratio=None,
            ev_ebitda=None,
            peg_ratio=None,
        )

        assert result.score == 5  # Neutral when no data


class TestQualityScoring:
    """Tests for quality score calculation."""

    def test_high_quality(self):
        """Test scoring for high-quality stock."""
        result = calculate_quality_score(
            roe=0.25,
            roic=0.20,
            debt_to_equity=0.3,
            gross_margin=0.50,
            gross_margin_trend=0.04,
        )

        assert isinstance(result, FactorScore)
        assert result.name == "Quality"
        assert result.score > 7  # High quality should score well

    def test_low_quality(self):
        """Test scoring for low-quality stock."""
        result = calculate_quality_score(
            roe=0.05,
            roic=-0.05,
            debt_to_equity=2.5,
            gross_margin=0.20,
            gross_margin_trend=-0.05,
        )

        assert result.score < 5  # Low quality should score poorly


class TestMomentumScoring:
    """Tests for momentum score calculation."""

    def test_bullish_momentum(self):
        """Test scoring for bullish momentum."""
        result = calculate_momentum_score(
            price=160.0,
            sma_50=150.0,
            sma_200=140.0,
            rsi_14=65.0,
        )

        assert isinstance(result, FactorScore)
        assert result.name == "Momentum"
        assert result.score > 6  # Good momentum should score well

    def test_bearish_momentum(self):
        """Test scoring for bearish momentum."""
        result = calculate_momentum_score(
            price=130.0,
            sma_50=145.0,
            sma_200=150.0,
            rsi_14=25.0,
        )

        assert result.score < 4  # Poor momentum should score poorly


class TestGrowthScoring:
    """Tests for growth score calculation."""

    def test_high_growth(self):
        """Test scoring for high-growth stock."""
        result = calculate_growth_score(
            revenue_growth_yoy=0.35,
            eps_growth_yoy=0.45,
            forward_revenue_growth=0.30,
            guidance_trend="raised",
        )

        assert isinstance(result, FactorScore)
        assert result.name == "Growth"
        assert result.score > 8  # High growth should score well

    def test_low_growth(self):
        """Test scoring for low-growth stock."""
        result = calculate_growth_score(
            revenue_growth_yoy=0.02,
            eps_growth_yoy=0.01,
            forward_revenue_growth=0.03,
            guidance_trend="lowered",
        )

        assert result.score < 4  # Low growth should score poorly


# =============================================================================
# TESTS FOR SCREENING FUNCTION
# =============================================================================

class TestScreeningFunction:
    """Tests for screen_stocks_with_scoring function."""

    def test_basic_screening(self, sample_stock_data, sample_prices, sample_technicals):
        """Test basic screening workflow."""
        results = screen_stocks_with_scoring(
            stocks=sample_stock_data,
            current_prices=sample_prices,
            technical_data=sample_technicals,
        )

        assert len(results) == 3
        assert all(isinstance(r, StockScreenResult) for r in results)
        assert all(0 <= r.total_score <= 10 for r in results)

    def test_results_sorted_by_score(self, sample_stock_data, sample_prices, sample_technicals):
        """Test that results are sorted by total score descending."""
        results = screen_stocks_with_scoring(
            stocks=sample_stock_data,
            current_prices=sample_prices,
            technical_data=sample_technicals,
        )

        # Check sorting
        for i in range(len(results) - 1):
            assert results[i].total_score >= results[i + 1].total_score

    def test_ranks_assigned(self, sample_stock_data, sample_prices, sample_technicals):
        """Test that ranks are assigned correctly."""
        results = screen_stocks_with_scoring(
            stocks=sample_stock_data,
            current_prices=sample_prices,
            technical_data=sample_technicals,
        )

        assert results[0].rank == 1
        assert results[1].rank == 2
        assert results[2].rank == 3

    def test_signals_assigned(self, sample_stock_data, sample_prices, sample_technicals):
        """Test that signals are assigned based on scores."""
        results = screen_stocks_with_scoring(
            stocks=sample_stock_data,
            current_prices=sample_prices,
            technical_data=sample_technicals,
        )

        for r in results:
            assert r.signal in ["STRONG BUY", "BUY", "HOLD", "AVOID", "STRONG AVOID"]


# =============================================================================
# TESTS FOR PROMPT GENERATION
# =============================================================================

class TestPromptGeneration:
    """Tests for prompt generation."""

    def test_generate_screener_prompt(self, sample_stock_data, sample_prices, sample_technicals):
        """Test generating screener prompt."""
        results = screen_stocks_with_scoring(
            stocks=sample_stock_data,
            current_prices=sample_prices,
            technical_data=sample_technicals,
        )

        prompt = generate_screener_prompt(
            tickers=[r.ticker for r in results],
            results=results,
        )

        assert isinstance(prompt, str)
        assert "AAPL" in prompt or "MSFT" in prompt or "GOOGL" in prompt
        assert "Leaderboard" in prompt or "leaderboard" in prompt


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self, sample_stock_data, sample_prices, sample_technicals):
        """Test complete screening workflow."""
        # Screen stocks
        results = screen_stocks_with_scoring(
            stocks=sample_stock_data,
            current_prices=sample_prices,
            technical_data=sample_technicals,
        )

        # Verify results
        assert len(results) == 3
        assert results[0].rank == 1

        # Generate prompt
        prompt = generate_screener_prompt(
            tickers=[r.ticker for r in results],
            results=results,
        )

        assert isinstance(prompt, str)
        assert len(prompt) > 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
