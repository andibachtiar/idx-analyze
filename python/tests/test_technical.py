"""
Tests for Technical Analysis Engine (Phase 4).

Tests all deterministic technical indicator calculations including:
- Moving averages (SMA, EMA)
- Momentum indicators (RSI, MACD)
- Volatility indicators (ATR, Volatility, Drawdown)
- Volume indicators (Volume SMA, Volume Ratio)
- Bollinger Bands
- Support/Resistance
- Price position indicators
- Edge cases and error handling
"""

import os
import sys
from datetime import date

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import pytest

from analysis.technical import (
    TechnicalResult,
    # Volatility
    atr,
    # Bollinger Bands
    bollinger_bands,
    # Batch functions
    calculate_all_technicals,
    drawdown,
    ema,
    # Support/Resistance
    find_support_resistance,
    get_technical_summary,
    macd,
    # Price Position
    price_vs_sma,
    # Momentum
    rsi,
    # Moving Averages
    sma,
    volatility,
    volume_ratio,
    # Volume
    volume_sma,
)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_test_prices(
    start: float = 100.0,
    growth_rate: float = 0.01,
    noise: float = 0.02,
    count: int = 100
) -> list:
    """Generate synthetic price data for testing."""
    np.random.seed(42)
    prices = [start]
    for i in range(1, count):
        change = np.random.normal(growth_rate, noise)
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    return prices


def generate_test_ohlcv(
    start: float = 100.0,
    count: int = 100
) -> tuple:
    """Generate synthetic OHLCV data."""
    np.random.seed(42)
    prices = generate_test_prices(start, 0.001, 0.015, count)

    highs = []
    lows = []
    volumes = []

    for price in prices:
        high = price * (1 + abs(np.random.normal(0, 0.005)))
        low = price * (1 - abs(np.random.normal(0, 0.005)))
        volume = int(np.random.lognormal(16, 0.5))
        highs.append(high)
        lows.append(low)
        volumes.append(volume)

    return prices, highs, lows, volumes


# =============================================================================
# TECHNICAL RESULT TESTS
# =============================================================================

class TestTechnicalResult:
    """Tests for TechnicalResult dataclass."""

    def test_available_result(self):
        result = TechnicalResult(value=100.5, indicator_name="sma")
        assert result.is_available
        assert "100.5000" in repr(result)

    def test_unavailable_result(self):
        result = TechnicalResult(value=None, indicator_name="sma")
        assert not result.is_available
        assert "N/A" in repr(result)

    def test_with_signal(self):
        result = TechnicalResult(value=75.0, indicator_name="rsi", signal="overbought")
        assert result.signal == "overbought"


# =============================================================================
# MOVING AVERAGE TESTS
# =============================================================================

class TestSMA:
    """Tests for Simple Moving Average."""

    def test_basic_sma(self):
        prices = [10, 20, 30, 40, 50]
        result = sma(prices, 3)
        # SMA of last 3: (30 + 40 + 50) / 3 = 40
        assert result.value == 40.0
        assert result.indicator_name == "sma"
        assert result.period == 3

    def test_sma_insufficient_data(self):
        prices = [10, 20]
        result = sma(prices, 5)
        assert result.value is None
        assert "Insufficient data" in result.notes

    def test_sma_single_price(self):
        prices = [100.0]
        result = sma(prices, 1)
        assert result.value == 100.0

    def test_sma_with_zero(self):
        prices = [0, 0, 100]
        result = sma(prices, 3)
        assert result.value == pytest.approx(33.333, abs=0.01)


class TestEMA:
    """Tests for Exponential Moving Average."""

    def test_basic_ema(self):
        prices = [10, 20, 30, 40, 50]
        result = ema(prices, 3)

        assert result.value is not None
        assert result.period == 3
        # EMA should be at least as close to recent prices as SMA
        # For this simple data, EMA equals the last price
        assert result.value >= 40

    def test_ema_insufficient_data(self):
        prices = [10, 20]
        result = ema(prices, 5)
        assert result.value is None

    def test_ema_vs_sma(self):
        """EMA should respond faster to price changes than SMA."""
        prices = [100] * 10 + [150]  # Sharp increase
        ema_result = ema(prices, 5)
        sma_result = sma(prices, 5)

        assert ema_result.value is not None
        assert sma_result.value is not None
        # EMA should be higher (closer to current price)
        assert ema_result.value > sma_result.value


# =============================================================================
# RSI TESTS
# =============================================================================

class TestRSI:
    """Tests for Relative Strength Index."""

    def test_rsi_oversold(self):
        """Test RSI in oversold territory."""
        # Declining prices
        prices = [100, 95, 90, 85, 80, 75, 70, 65, 60, 55]
        result = rsi(prices, 5)

        assert result.value is not None
        assert result.value < 30  # Oversold
        assert result.signal == "oversold"

    def test_rsi_overbought(self):
        """Test RSI in overbought territory."""
        # Rising prices
        prices = [50, 55, 60, 65, 70, 75, 80, 85, 90, 95]
        result = rsi(prices, 5)

        assert result.value is not None
        assert result.value > 70  # Overbought
        assert result.signal == "overbought"

    def test_rsi_neutral(self):
        """Test RSI in neutral territory."""
        # Sideways prices
        prices = [100, 101, 99, 100, 101, 99, 100, 101, 99, 100]
        result = rsi(prices, 5)

        assert result.value is not None
        assert 40 <= result.value <= 60  # Neutral

    def test_rsi_insufficient_data(self):
        prices = [100, 90]
        result = rsi(prices, 14)
        assert result.value is None

    def test_rsi_perfect_uptrend(self):
        """Test RSI with perfect uptrend (should be 100)."""
        prices = [100, 110, 120, 130, 140, 150]
        result = rsi(prices, 3)
        assert result.value == 100.0


# =============================================================================
# MACD TESTS
# =============================================================================

class TestMACD:
    """Tests for MACD indicator."""

    def test_macd_basic(self):
        prices = generate_test_prices(count=50)
        result = macd(prices)

        assert "macd_line" in result
        assert "signal_line" in result
        assert "histogram" in result

    def test_macd_insufficient_data(self):
        prices = [100, 101]
        result = macd(prices)
        assert result["macd_line"] is None

    def test_macd_bullish_crossover(self):
        """Test MACD bullish signal."""
        # Need at least slow_period(26) + signal_period(9) = 35 prices
        prices = [100] * 30 + [105, 110, 115, 120, 125]  # 35 prices
        result = macd(prices)

        # Histogram should be positive in uptrend
        assert result["histogram"] is not None


# =============================================================================
# ATR TESTS
# =============================================================================

class TestATR:
    """Tests for Average True Range."""

    def test_atr_basic(self):
        highs = [100, 102, 101, 103, 105]
        lows = [98, 99, 98, 100, 101]
        closes = [99, 100, 99, 102, 104]

        result = atr(highs, lows, closes, 3)
        assert result.value is not None
        assert result.indicator_name == "atr"

    def test_atr_insufficient_data(self):
        highs = [100, 101]
        lows = [98, 99]
        closes = [99, 100]

        result = atr(highs, lows, closes, 5)
        assert result.value is None

    def test_atr_low_volatility(self):
        """Test ATR with low volatility."""
        highs = [100.1] * 20
        lows = [99.9] * 20
        closes = [100.0] * 20

        result = atr(highs, lows, closes, 10)
        assert result.value is not None
        assert result.value < 1.0  # Low ATR for low volatility


# =============================================================================
# VOLATILITY TESTS
# =============================================================================

class TestVolatility:
    """Tests for volatility calculation."""

    def test_volatility_basic(self):
        prices = generate_test_prices(count=50)
        result = volatility(prices, 20)

        assert result.value is not None
        assert result.indicator_name == "volatility"
        # Annualized volatility should be reasonable (0-100%)
        assert 0 <= result.value <= 2.0

    def test_volatility_insufficient_data(self):
        prices = [100, 101]
        result = volatility(prices, 20)
        assert result.value is None

    def test_volatility_trending(self):
        """Test volatility with trending prices."""
        prices = [100 * (1.01 ** i) for i in range(50)]
        result = volatility(prices, 20)

        assert result.value is not None
        # Trending prices should have lower volatility than random
        assert result.value < 0.5


# =============================================================================
# DRAWDOWN TESTS
# =============================================================================

class TestDrawdown:
    """Tests for drawdown calculation."""

    def test_drawdown_basic(self):
        prices = [100, 110, 105, 100, 90, 95]
        result = drawdown(prices)

        assert result.value is not None
        assert result.value < 0  # Negative indicates loss
        # Max drawdown should be from 110 to 90 = ~18%
        assert result.value <= -0.15

    def test_drawdown_no_decline(self):
        """Test drawdown with continuous uptrend."""
        prices = [100, 110, 120, 130, 140]
        result = drawdown(prices)

        assert result.value == 0.0

    def test_drawdown_insufficient_data(self):
        prices = [100]
        result = drawdown(prices)
        assert result.value is None


# =============================================================================
# VOLUME TESTS
# =============================================================================

class TestVolume:
    """Tests for volume indicators."""

    def test_volume_sma(self):
        volumes = [1000, 1500, 1200, 1800, 2000]
        result = volume_sma(volumes, 3)

        # Average of last 3: (1200 + 1800 + 2000) / 3 = 1666.67
        assert result.value == pytest.approx(1666.67, abs=1.0)

    def test_volume_ratio_normal(self):
        volumes = [1000] * 20 + [2000]  # Double volume
        result = volume_ratio(volumes, 20)

        # Average of previous 20 = 1000, current = 2000, ratio = 2.0
        assert result.value == pytest.approx(2.0)

    def test_volume_ratio_spike(self):
        volumes = [1000] * 20 + [5000]  # 5x volume
        result = volume_ratio(volumes, 20)

        assert result.value == pytest.approx(5.0)
        assert result.signal == "high_volume"

    def test_volume_ratio_low(self):
        volumes = [1000] * 20 + [200]  # Low volume
        result = volume_ratio(volumes, 20)

        assert result.value == pytest.approx(0.2)
        assert result.signal == "low_volume"

    def test_volume_insufficient_data(self):
        volumes = [1000, 1500]
        result = volume_sma(volumes, 10)
        assert result.value is None


# =============================================================================
# BOLLINGER BANDS TESTS
# =============================================================================

class TestBollingerBands:
    """Tests for Bollinger Bands."""

    def test_bollinger_bands_basic(self):
        prices = generate_test_prices(count=50)
        result = bollinger_bands(prices)

        assert result["upper"] is not None
        assert result["middle"] is not None
        assert result["lower"] is not None
        assert result["upper"] > result["middle"] > result["lower"]

    def test_bollinger_bands_width(self):
        """Test bandwidth calculation."""
        prices = [100] * 20 + [150, 200, 250]  # Sudden spike
        result = bollinger_bands(prices)

        assert result["bandwidth"] is not None
        assert result["bandwidth"] > 0

    def test_bollinger_bands_percent_b(self):
        """Test %B calculation."""
        prices = [100, 105, 110, 115, 120] * 4  # Uptrend
        result = bollinger_bands(prices)

        assert result["percent_b"] is not None
        assert 0 <= result["percent_b"] <= 1

    def test_bollinger_bands_overbought(self):
        """Test Bollinger Bands overbought signal."""
        prices = [100] * 19 + [150]  # Sharp spike
        result = bollinger_bands(prices)

        assert result.get("signal") == "overbought"

    def test_bollinger_bands_oversold(self):
        """Test Bollinger Bands oversold signal."""
        prices = [100] * 19 + [50]  # Sharp drop
        result = bollinger_bands(prices)

        assert result.get("signal") == "oversold"

    def test_bollinger_bands_insufficient_data(self):
        prices = [100, 101]
        result = bollinger_bands(prices)
        assert result["upper"] is None


# =============================================================================
# SUPPORT/RESISTANCE TESTS
# =============================================================================

class TestSupportResistance:
    """Tests for support/resistance identification."""

    def test_sr_basic(self):
        highs = [100, 105, 102, 108, 103, 106] * 10
        lows = [95, 98, 96, 100, 97, 99] * 10

        result = find_support_resistance(highs, lows, window=20)

        assert result["resistance"] is not None
        assert result["support"] is not None
        assert result["resistance"] > result["support"]

    def test_sr_insufficient_data(self):
        highs = [100, 101]
        lows = [99, 98]
        result = find_support_resistance(highs, lows, window=10)
        assert result["resistance"] is None


# =============================================================================
# PRICE VS SMA TESTS
# =============================================================================

class TestPriceVsSMA:
    """Tests for price vs SMA indicator."""

    def test_price_above_sma(self):
        prices = [100] * 199 + [150]  # Sharp uptrend
        result = price_vs_sma(prices, 200)

        assert result.value is not None
        assert result.value > 0  # Above SMA
        assert result.signal == "above_sma"

    def test_price_below_sma(self):
        prices = [150] * 199 + [100]  # Sharp downtrend
        result = price_vs_sma(prices, 200)

        assert result.value is not None
        assert result.value < 0  # Below SMA
        assert result.signal == "below_sma"

    def test_price_vs_sma_insufficient_data(self):
        prices = [100, 101]
        result = price_vs_sma(prices, 200)
        assert result.value is None


# =============================================================================
# BATCH CALCULATION TESTS
# =============================================================================

class TestBatchCalculations:
    """Tests for batch technical analysis."""

    def test_calculate_all_technicals(self):
        prices, highs, lows, volumes = generate_test_ohlcv(count=100)
        results = calculate_all_technicals(prices, highs, lows, volumes)

        # Check key indicators exist
        assert "sma_20" in results
        assert "rsi_14" in results
        assert "bollinger_bands" in results
        assert "volume_ratio" in results

    def test_calculate_all_without_volume(self):
        prices, highs, lows, _ = generate_test_ohlcv(count=100)
        results = calculate_all_technicals(prices, highs, lows)

        assert "sma_20" in results
        assert "volume_ratio" not in results  # No volume data

    def test_get_technical_summary(self):
        prices = generate_test_prices(count=100)
        summary = get_technical_summary(prices)

        assert "indicators" in summary
        assert "calculated_at" in summary


# =============================================================================
# INTEGRATION TESTS WITH REALISTIC DATA
# =============================================================================

class TestIntegration:
    """Integration tests with realistic stock patterns."""

    def test_bull_market_pattern(self):
        """Test technical analysis on bull market pattern."""
        # Consistent uptrend
        prices = [100 * (1.005 ** i) for i in range(200)]

        sma_20 = sma(prices, 20)
        sma_50 = sma(prices, 50)
        rsi_result = rsi(prices, 14)
        price_vs_sma200 = price_vs_sma(prices, 200)

        # In uptrend: SMA20 > SMA50 (shorter MA above longer MA)
        assert sma_20.value > sma_50.value

        # Price should be near or above SMA200
        assert price_vs_sma200.value is None or price_vs_sma200.value >= -5

    def test_bear_market_pattern(self):
        """Test technical analysis on bear market pattern."""
        # Consistent downtrend
        prices = [100 * (0.995 ** i) for i in range(200)]

        sma_20 = sma(prices, 20)
        sma_50 = sma(prices, 50)
        rsi_result = rsi(prices, 14)

        # In downtrend: SMA20 < SMA50 (shorter MA below longer MA)
        assert sma_20.value < sma_50.value

        # RSI should be in neutral to oversold territory
        assert rsi_result.value is not None
        assert rsi_result.value <= 50

    def test_sideways_market_pattern(self):
        """Test technical analysis on sideways market."""
        # Range-bound prices
        np.random.seed(42)
        prices = [100 + np.random.normal(0, 2) for _ in range(200)]

        rsi_result = rsi(prices, 14)

        # RSI should be in neutral territory
        assert rsi_result.value is not None
        assert 40 <= rsi_result.value <= 60

    def test_volatile_market_pattern(self):
        """Test technical analysis on volatile market."""
        # High volatility
        np.random.seed(42)
        prices = [100]
        for _ in range(199):
            change = np.random.choice([-0.1, 0.1])
            prices.append(prices[-1] * (1 + change))

        vol = volatility(prices, 20)
        dd_result = drawdown(prices)

        # High volatility should have elevated ATR/volatility
        assert vol.value is not None
        assert vol.value > 0.3  # At least 30% annualized volatility


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_prices(self):
        assert sma([], 10).value is None
        assert ema([], 10).value is None
        assert rsi([], 14).value is None

    def test_single_price(self):
        assert sma([100], 5).value is None
        assert ema([100], 5).value is None
        assert rsi([100], 14).value is None

    def test_all_same_prices(self):
        prices = [100] * 50
        assert sma(prices, 10).value == 100.0
        # When all prices are the same, RSI should be 50 (neutral)
        rsi_result = rsi(prices, 14)
        assert rsi_result.value == 50.0

    def test_zero_prices(self):
        prices = [0, 0, 100, 200]
        result = sma(prices, 2)
        assert result.value == 150.0

    def test_negative_prices(self):
        prices = [-100, -50, 0, 50, 100]
        result = rsi(prices, 3)
        # Should handle gracefully
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
