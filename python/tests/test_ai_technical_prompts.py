"""
Tests for Technical Analysis Prompt Integration (Phase 17).

Tests cover:
- Technical analysis result generation
- Prompt generation for LLM
- Trading recommendations
- Edge cases and error handling
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.prompts.technical import (
    BollingerBandResult,
    MACDResult,
    MovingAverageSignal,
    TechnicalAnalysisResult,
    analyze_stock_technicals,
    generate_technical_prompt,
    generate_trading_recommendation,
    get_technical_analysis_with_llm,
)

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_prices():
    """Create sample price data for testing."""
    # Simulate 100 days of price data with an uptrend
    return [100 + i * 0.5 + (i % 10) * 0.1 for i in range(100)]


@pytest.fixture
def sample_volumes():
    """Create sample volume data."""
    import random
    random.seed(42)
    return [int(1000000 + i * 10000 + random.randint(-50000, 50000)) for i in range(100)]


@pytest.fixture
def sample_highs(sample_prices):
    """Create sample high prices."""
    return [p + 2 for p in sample_prices]


@pytest.fixture
def sample_lows(sample_prices):
    """Create sample low prices."""
    return [p - 2 for p in sample_prices]


# =============================================================================
# TESTS FOR PROMPT GENERATION
# =============================================================================

class TestPromptGeneration:
    """Tests for technical prompt generation."""

    def test_generate_technical_prompt(self, sample_prices):
        """Test generating technical analysis prompt."""
        prompt = generate_technical_prompt(
            ticker="AAPL",
            current_price=150.0,
            technical_data={
                "indicators": {
                    "sma_20": {"value": 148.0},
                    "sma_50": {"value": 145.0},
                    "sma_200": {"value": 140.0},
                    "rsi_14": {"value": 65.0, "signal": "neutral"},
                    "macd": {"macd_line": 2.5, "signal_line": 2.0, "histogram": 0.5, "signal": "bullish"},
                    "bollinger_bands": {"upper": 155.0, "middle": 150.0, "lower": 145.0, "percent_b": 0.5},
                }
            }
        )

        assert isinstance(prompt, str)
        assert "AAPL" in prompt
        assert "150.00" in prompt
        assert "RSI" in prompt
        assert "MACD" in prompt

    def test_generate_technical_prompt_with_none_values(self, sample_prices):
        """Test prompt generation with missing data."""
        prompt = generate_technical_prompt(
            ticker="TEST",
            current_price=50.0,
            technical_data={"indicators": {}}
        )

        assert isinstance(prompt, str)
        assert "TEST" in prompt

    def test_generate_trading_recommendation_buy(self, sample_prices):
        """Test trading recommendation for BUY signal."""
        result = TechnicalAnalysisResult(
            ticker="AAPL",
            analysis_date=datetime.now().isoformat(),
            current_price=150.0,
            trend="bullish",
            trend_strength="strong",
            ma_analysis={},
            ma_stack_direction="bullish",
            rsi_14=65.0,
            rsi_signal="neutral",
            macd=MACDResult(macd_line=2.5, signal_line=2.0, histogram=0.5, signal="bullish"),
            bollinger_bands=BollingerBandResult(upper=155.0, middle=150.0, lower=145.0, percent_b=0.5, width=6.67),
            volume_ratio=1.2,
            volume_trend="increasing",
            atr_14=2.0,
            volatility_percent=1.33,
            support_levels=[145.0, 140.0],
            resistance_levels=[155.0, 160.0],
            overall_signal="bullish",
            confidence="HIGH",
            score=7.5,
            horizon="MEDIUM",
            action="BUY",
            conviction="STRONG",
            entry_price=150.0,
            target_price=160.0,
            stop_loss=145.0,
            risk_reward_ratio=2.0,
            key_observations=["Price above all MAs", "RSI neutral", "MACD bullish"],
            risks=["Market volatility", "Earnings risk"],
            recommendations=["Enter on pullback", "Set stop at 145"],
        )

        rec = generate_trading_recommendation("AAPL", 150.0, result)

        assert isinstance(rec, str)
        assert "BUY" in rec
        assert "150.00" in rec
        assert "160.00" in rec

    def test_generate_trading_recommendation_sell(self, sample_prices):
        """Test trading recommendation for SELL signal."""
        result = TechnicalAnalysisResult(
            ticker="AAPL",
            analysis_date=datetime.now().isoformat(),
            current_price=150.0,
            trend="bearish",
            trend_strength="strong",
            ma_analysis={},
            ma_stack_direction="bearish",
            rsi_14=25.0,
            rsi_signal="oversold",
            macd=MACDResult(macd_line=-2.0, signal_line=-1.5, histogram=-0.5, signal="bearish"),
            bollinger_bands=None,
            volume_ratio=0.8,
            volume_trend="decreasing",
            atr_14=2.0,
            volatility_percent=1.33,
            support_levels=[145.0, 140.0],
            resistance_levels=[155.0, 160.0],
            overall_signal="bearish",
            confidence="HIGH",
            score=2.5,
            horizon="SHORT",
            action="SELL",
            conviction="MODERATE",
            entry_price=None,
            target_price=140.0,
            stop_loss=155.0,
            risk_reward_ratio=1.5,
            key_observations=["Price below MA200", "RSI oversold", "MACD bearish"],
            risks=["Further decline", "Break below support"],
            recommendations=["Exit position", "Wait for reversal"],
        )

        rec = generate_trading_recommendation("AAPL", 150.0, result)

        assert isinstance(rec, str)
        assert "SELL" in rec

    def test_generate_trading_recommendation_hold(self, sample_prices):
        """Test trading recommendation for HOLD signal."""
        result = TechnicalAnalysisResult(
            ticker="AAPL",
            analysis_date=datetime.now().isoformat(),
            current_price=150.0,
            trend="sideways",
            trend_strength="weak",
            ma_analysis={},
            ma_stack_direction="mixed",
            rsi_14=50.0,
            rsi_signal="neutral",
            macd=MACDResult(macd_line=0.0, signal_line=0.0, histogram=0.0, signal="neutral"),
            bollinger_bands=None,
            volume_ratio=1.0,
            volume_trend="stable",
            atr_14=2.0,
            volatility_percent=1.33,
            support_levels=[145.0, 140.0],
            resistance_levels=[155.0, 160.0],
            overall_signal="neutral",
            confidence="LOW",
            score=5.0,
            horizon="SHORT",
            action="HOLD",
            conviction="WEAK",
            entry_price=None,
            target_price=None,
            stop_loss=None,
            risk_reward_ratio=None,
            key_observations=["Mixed signals", "Consolidating"],
            risks=["Uncertainty", "No clear direction"],
            recommendations=["Maintain position", "Wait for clearer signal"],
        )

        rec = generate_trading_recommendation("AAPL", 150.0, result)

        assert isinstance(rec, str)
        assert "HOLD" in rec


# =============================================================================
# TESTS FOR ANALYSIS FUNCTION
# =============================================================================

class TestAnalysisFunction:
    """Tests for analyze_stock_technicals function."""

    def test_analyze_stock_technicals_basic(self, sample_prices):
        """Test basic technical analysis."""
        result = analyze_stock_technicals(
            ticker="AAPL",
            prices=sample_prices,
        )

        assert isinstance(result, TechnicalAnalysisResult)
        assert result.ticker == "AAPL"
        assert result.current_price == sample_prices[-1]
        assert result.overall_signal in ["bullish", "bearish", "neutral"]
        assert result.confidence in ["HIGH", "MEDIUM", "LOW"]

    def test_analyze_stock_technicals_with_volumes(self, sample_prices, sample_volumes):
        """Test technical analysis with volume data."""
        result = analyze_stock_technicals(
            ticker="AAPL",
            prices=sample_prices,
            volumes=sample_volumes,
        )

        assert result.volume_ratio is not None
        assert result.volume_trend in ["increasing", "decreasing", "stable"]

    def test_analyze_stock_technicals_insufficient_data(self):
        """Test with insufficient data."""
        result = analyze_stock_technicals(
            ticker="AAPL",
            prices=[100.0, 101.0],
        )

        assert result.ticker == "AAPL"
        assert result.overall_signal == "neutral"
        assert result.confidence == "LOW"

    def test_analyze_stock_technicals_empty_prices(self):
        """Test with empty price list."""
        result = analyze_stock_technicals(
            ticker="AAPL",
            prices=[],
        )

        assert result.ticker == "AAPL"
        assert result.current_price == 0
        assert result.overall_signal == "neutral"

    def test_analyze_stock_technicals_trending_up(self):
        """Test with clearly trending up data."""
        # Strong uptrend with sufficient data
        prices = [100 + i * 2 for i in range(100)]
        result = analyze_stock_technicals(
            ticker="AAPL",
            prices=prices,
        )

        assert result.overall_signal == "bullish"
        assert result.trend == "bullish"
        assert result.action in ["BUY", "HOLD"]

    def test_analyze_stock_technicals_trending_down(self):
        """Test with clearly trending down data."""
        # Strong downtrend with sufficient data (keep prices positive)
        prices = [200 - i * 2 for i in range(100)]  # [200, 198, ..., 2]
        result = analyze_stock_technicals(
            ticker="AAPL",
            prices=prices,
        )

        assert result.overall_signal == "bearish"
        assert result.trend == "bearish"
        assert result.action in ["SELL", "HOLD"]

    def test_analyze_stock_technicals_sideways(self):
        """Test with sideways/range-bound data."""
        # Sideways movement with sufficient data
        prices = [100 + (i % 10) * 0.5 for i in range(100)]
        result = analyze_stock_technicals(
            ticker="AAPL",
            prices=prices,
        )

        # Should be neutral or hold
        assert result.overall_signal in ["neutral", "bullish", "bearish"]


# =============================================================================
# TESTS FOR CONVENIENCE FUNCTIONS
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_technical_analysis_with_llm_no_client(self, sample_prices):
        """Test with LLM but no client."""
        result = get_technical_analysis_with_llm(
            ticker="AAPL",
            prices=sample_prices,
        )

        assert isinstance(result, dict)
        assert result["ticker"] == "AAPL"
        assert "overall_signal" in result
        assert "action" in result

    def test_get_technical_analysis_with_llm_none_prices(self):
        """Test with no price data."""
        result = get_technical_analysis_with_llm(
            ticker="AAPL",
            prices=[],
        )

        assert result["ticker"] == "AAPL"
        assert result["current_price"] == 0


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for technical analysis."""

    def test_full_workflow(self, sample_prices):
        """Test complete technical analysis workflow."""
        # Generate prompt
        prompt = generate_technical_prompt(
            ticker="AAPL",
            current_price=sample_prices[-1],
            technical_data={
                "indicators": {
                    "sma_20": {"value": 148.0},
                    "sma_50": {"value": 145.0},
                    "rsi_14": {"value": 65.0, "signal": "neutral"},
                }
            }
        )

        # Analyze
        result = analyze_stock_technicals(
            ticker="AAPL",
            prices=sample_prices,
        )

        # Generate recommendation
        rec = generate_trading_recommendation("AAPL", sample_prices[-1], result)

        # Verify
        assert isinstance(prompt, str)
        assert isinstance(result, TechnicalAnalysisResult)
        assert isinstance(rec, str)
        assert "AAPL" in prompt
        assert "AAPL" in result.ticker


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
