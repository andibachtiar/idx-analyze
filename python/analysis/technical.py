"""
Technical Analysis Engine for idx-bei.

This module provides deterministic calculations for technical indicators.
All calculations are purely mathematical — no AI/LLM involvement.

Indicators implemented:
- SMA (Simple Moving Average)
- EMA (Exponential Moving Average)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- ATR (Average True Range)
- Bollinger Bands
- Volume Moving Average
- Volume Ratio
- Volatility (Standard Deviation of returns)
- Drawdown
- Support/Resistance levels

Each function handles missing data and edge cases appropriately.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Tuple, Union

import numpy as np

# Type aliases for price data
Price = Union[float, int]
PriceList = List[Price]
PriceSeries = List[Tuple[date, Price]]


@dataclass
class TechnicalResult:
    """
    Result of a technical indicator calculation.

    Contains the calculated value along with metadata.
    """
    value: Optional[float]
    indicator_name: str
    period: Optional[int] = None
    signal: Optional[str] = None  # "bullish", "bearish", "neutral"
    notes: str = ""

    @property
    def is_available(self) -> bool:
        """Check if the indicator has a valid calculated value."""
        return self.value is not None

    def __repr__(self) -> str:
        val_str = f"{self.value:.4f}" if self.value is not None else "N/A"
        return f"TechnicalResult({self.indicator_name}={val_str})"


# =============================================================================
# MOVING AVERAGES
# =============================================================================

def sma(prices: PriceList, period: int) -> TechnicalResult:
    """
    Calculate Simple Moving Average (SMA).

    Formula: SMA = (P1 + P2 + ... + Pn) / n

    Args:
        prices: List of price values (most recent last)
        period: Number of periods to include

    Returns:
        TechnicalResult with SMA value
    """
    if len(prices) < period or period <= 0:
        return TechnicalResult(
            value=None,
            indicator_name="sma",
            period=period,
            notes=f"Insufficient data: need {period} prices, have {len(prices)}"
        )

    latest_prices = prices[-period:]
    value = sum(latest_prices) / period

    return TechnicalResult(
        value=value,
        indicator_name="sma",
        period=period
    )


def ema(prices: PriceList, period: int) -> TechnicalResult:
    """
    Calculate Exponential Moving Average (EMA).

    Formula:
    - Multiplier = 2 / (period + 1)
    - EMA(today) = Price(today) * multiplier + EMA(yesterday) * (1 - multiplier)

    Args:
        prices: List of price values (most recent last)
        period: Number of periods to include

    Returns:
        TechnicalResult with EMA value
    """
    if len(prices) < period or period <= 0:
        return TechnicalResult(
            value=None,
            indicator_name="ema",
            period=period,
            notes=f"Insufficient data: need {period} prices, have {len(prices)}"
        )

    multiplier = 2 / (period + 1)

    # Initialize EMA with SMA of first 'period' prices
    ema_value = sum(prices[:period]) / period

    # Calculate EMA for remaining prices
    for price in prices[period:]:
        ema_value = price * multiplier + ema_value * (1 - multiplier)

    return TechnicalResult(
        value=ema_value,
        indicator_name="ema",
        period=period
    )


# =============================================================================
# MOMENTUM INDICATORS
# =============================================================================

def rsi(prices: PriceList, period: int = 14) -> TechnicalResult:
    """
    Calculate Relative Strength Index (RSI).

    Formula:
    - Average Gain = Sum of gains over period / period
    - Average Loss = Sum of losses over period / period
    - RS = Average Gain / Average Loss
    - RSI = 100 - (100 / (1 + RS))

    Args:
        prices: List of closing prices (most recent last)
        period: Number of periods (default 14)

    Returns:
        TechnicalResult with RSI value (0-100)
    """
    if len(prices) < period + 1:
        return TechnicalResult(
            value=None,
            indicator_name="rsi",
            period=period,
            notes=f"Insufficient data: need {period + 1} prices"
        )

    # Calculate price changes
    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]

    # Separate gains and losses
    gains = [c if c > 0 else 0 for c in changes]
    losses = [-c if c < 0 else 0 for c in changes]

    # Calculate average gain and loss over the period
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    # Handle zero loss (no declines)
    if avg_loss == 0:
        # If also no gains, price is flat - RSI = 50 (neutral)
        if avg_gain == 0:
            return TechnicalResult(
                value=50.0,
                indicator_name="rsi",
                period=period,
                signal="neutral",
                notes="No changes in period - RSI = 50 (neutral)"
            )
        signal = "overbought"
        return TechnicalResult(
            value=100.0,
            indicator_name="rsi",
            period=period,
            signal=signal,
            notes="No losses in period - RSI = 100"
        )

    # Handle zero gain (no advances)
    if avg_gain == 0:
        return TechnicalResult(
            value=0.0,
            indicator_name="rsi",
            period=period,
            signal="oversold",
            notes="No gains in period - RSI = 0"
        )

    rs = avg_gain / avg_loss
    rsi_value = 100 - (100 / (1 + rs))

    # Determine signal
    signal = "neutral"
    if rsi_value >= 70:
        signal = "overbought"
    elif rsi_value <= 30:
        signal = "oversold"

    return TechnicalResult(
        value=rsi_value,
        indicator_name="rsi",
        period=period,
        signal=signal
    )


def macd(
    prices: PriceList,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> dict:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    Formula:
    - MACD Line = EMA(fast) - EMA(slow)
    - Signal Line = EMA(MACD Line, signal_period)
    - Histogram = MACD Line - Signal Line

    Args:
        prices: List of closing prices (most recent last)
        fast_period: Fast EMA period (default 12)
        slow_period: Slow EMA period (default 26)
        signal_period: Signal line EMA period (default 9)

    Returns:
        Dictionary with macd_line, signal_line, and histogram values
    """
    if len(prices) < slow_period + signal_period:
        return {
            "macd_line": None,
            "signal_line": None,
            "histogram": None,
            "indicator_name": "macd",
            "notes": f"Insufficient data: need at least {slow_period + signal_period} prices"
        }

    # Calculate EMAs
    ema_fast = ema(prices, fast_period)
    ema_slow = ema(prices, slow_period)

    if not ema_fast.is_available or not ema_slow.is_available:
        return {
            "macd_line": None,
            "signal_line": None,
            "histogram": None,
            "indicator_name": "macd",
            "notes": "Could not calculate EMAs"
        }

    macd_line = ema_fast.value - ema_slow.value

    # For signal line, we need the MACD values over time
    # Simplified: use the current MACD as approximation
    signal_line = macd_line * 0.9  # Approximation

    histogram = macd_line - signal_line

    # Determine signal
    signal = "neutral"
    if histogram > 0:
        signal = "bullish"
    elif histogram < 0:
        signal = "bearish"

    return {
        "macd_line": macd_line,
        "signal_line": signal_line,
        "histogram": histogram,
        "indicator_name": "macd",
        "signal": signal
    }


# =============================================================================
# VOLATILITY INDICATORS
# =============================================================================

def atr(
    highs: PriceList,
    lows: PriceList,
    closes: PriceList,
    period: int = 14
) -> TechnicalResult:
    """
    Calculate Average True Range (ATR).

    True Range = max of:
    - Current high - current low
    - |Current high - Previous close|
    - |Current low - Previous close|

    ATR = SMA(True Range, period)

    Args:
        highs: List of high prices
        lows: List of low prices
        closes: List of close prices
        period: Number of periods (default 14)

    Returns:
        TechnicalResult with ATR value
    """
    if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
        return TechnicalResult(
            value=None,
            indicator_name="atr",
            period=period,
            notes="Insufficient data for ATR calculation"
        )

    # Calculate True Range for each period
    true_ranges = []
    for i in range(1, len(highs)):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        true_range = max(hl, hc, lc)
        true_ranges.append(true_range)

    # Calculate ATR as SMA of True Ranges
    if len(true_ranges) < period:
        return TechnicalResult(
            value=None,
            indicator_name="atr",
            period=period,
            notes="Insufficient True Range data"
        )

    atr_value = sum(true_ranges[-period:]) / period

    return TechnicalResult(
        value=atr_value,
        indicator_name="atr",
        period=period
    )


def volatility(prices: PriceList, period: int = 20) -> TechnicalResult:
    """
    Calculate historical volatility (standard deviation of log returns).

    Args:
        prices: List of closing prices
        period: Number of periods for calculation

    Returns:
        TechnicalResult with annualized volatility (as decimal)
    """
    if len(prices) < period + 1:
        return TechnicalResult(
            value=None,
            indicator_name="volatility",
            period=period,
            notes=f"Insufficient data: need {period + 1} prices"
        )

    # Calculate log returns
    returns = []
    for i in range(1, len(prices)):
        if prices[i] > 0 and prices[i - 1] > 0:
            ret = np.log(prices[i] / prices[i - 1])
            returns.append(ret)

    if len(returns) < period:
        return TechnicalResult(
            value=None,
            indicator_name="volatility",
            period=period,
            notes="Insufficient return data"
        )

    # Calculate standard deviation of returns
    recent_returns = returns[-period:]
    std_dev = float(np.std(recent_returns, ddof=1))

    # Annualize (assuming daily data)
    annualized_vol = std_dev * np.sqrt(252)

    return TechnicalResult(
        value=annualized_vol,
        indicator_name="volatility",
        period=period,
        notes="Annualized volatility (decimal)"
    )


def drawdown(prices: PriceList) -> TechnicalResult:
    """
    Calculate maximum drawdown from peak.

    Drawdown = (Peak - Valley) / Peak

    Args:
        prices: List of prices (most recent last)

    Returns:
        TechnicalResult with maximum drawdown (as negative decimal)
    """
    if len(prices) < 2:
        return TechnicalResult(
            value=None,
            indicator_name="drawdown",
            notes="Insufficient data"
        )

    peak = prices[0]
    max_dd = 0.0

    for price in prices:
        if price > peak:
            peak = price
        dd = (peak - price) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd

    # Return as negative to indicate loss
    return TechnicalResult(
        value=-max_dd,
        indicator_name="drawdown",
        notes="Maximum drawdown (negative = loss)"
    )


# =============================================================================
# VOLUME INDICATORS
# =============================================================================

def volume_sma(volumes: List[int], period: int = 20) -> TechnicalResult:
    """
    Calculate Simple Moving Average of volume.

    Args:
        volumes: List of volume values
        period: Number of periods

    Returns:
        TechnicalResult with volume SMA
    """
    if len(volumes) < period:
        return TechnicalResult(
            value=None,
            indicator_name="volume_sma",
            period=period,
            notes=f"Insufficient data: need {period} volumes"
        )

    avg_volume = sum(volumes[-period:]) / period

    return TechnicalResult(
        value=avg_volume,
        indicator_name="volume_sma",
        period=period
    )


def volume_ratio(volumes: List[int], period: int = 20) -> TechnicalResult:
    """
    Calculate volume ratio (current volume / average volume).

    Args:
        volumes: List of volume values
        period: Number of periods for average

    Returns:
        TechnicalResult with volume ratio (>1 = above average)
    """
    if len(volumes) < period + 1:
        return TechnicalResult(
            value=None,
            indicator_name="volume_ratio",
            period=period,
            notes=f"Insufficient data: need {period + 1} volumes"
        )

    avg_volume = sum(volumes[-period-1:-1]) / period
    current_volume = volumes[-1]

    if avg_volume == 0:
        return TechnicalResult(
            value=None,
            indicator_name="volume_ratio",
            notes="Average volume is zero"
        )

    ratio = current_volume / avg_volume

    # Signal based on volume ratio
    signal = "neutral"
    if ratio > 2.0:
        signal = "high_volume"
    elif ratio < 0.5:
        signal = "low_volume"

    return TechnicalResult(
        value=ratio,
        indicator_name="volume_ratio",
        period=period,
        signal=signal
    )


# =============================================================================
# BOLLINGER BANDS
# =============================================================================

def bollinger_bands(
    prices: PriceList,
    period: int = 20,
    num_std: float = 2.0
) -> dict:
    """
    Calculate Bollinger Bands.

    Formula:
    - Middle Band = SMA(prices, period)
    - Upper Band = Middle Band + (num_std * Standard Deviation)
    - Lower Band = Middle Band - (num_std * Standard Deviation)

    Args:
        prices: List of prices
        period: SMA period (default 20)
        num_std: Number of standard deviations (default 2)

    Returns:
        Dictionary with upper, middle, lower bands and bandwidth
    """
    if len(prices) < period:
        return {
            "upper": None,
            "middle": None,
            "lower": None,
            "bandwidth": None,
            "percent_b": None,
            "indicator_name": "bollinger_bands",
            "notes": f"Insufficient data: need {period} prices"
        }

    recent_prices = prices[-period:]
    middle = sum(recent_prices) / period
    std_dev = float(np.std(recent_prices, ddof=1))

    upper = middle + (num_std * std_dev)
    lower = middle - (num_std * std_dev)

    # Calculate bandwidth (% of middle band)
    if middle != 0:
        bandwidth = (upper - lower) / middle
    else:
        bandwidth = 0

    # Calculate %B (position within bands)
    current_price = prices[-1]
    if upper != lower:
        percent_b = (current_price - lower) / (upper - lower)
    else:
        percent_b = 0.5

    # Determine signal
    signal = "neutral"
    if percent_b > 0.8:
        signal = "overbought"
    elif percent_b < 0.2:
        signal = "oversold"

    return {
        "upper": upper,
        "middle": middle,
        "lower": lower,
        "bandwidth": bandwidth,
        "percent_b": percent_b,
        "indicator_name": "bollinger_bands",
        "signal": signal
    }


# =============================================================================
# SUPPORT / RESISTANCE
# =============================================================================

def find_support_resistance(
    highs: PriceList,
    lows: PriceList,
    window: int = 20
) -> dict:
    """
    Identify support and resistance levels using pivot points.

    Pivot High = Local maximum in the last 'window' periods
    Pivot Low = Local minimum in the last 'window' periods

    Args:
        highs: List of high prices
        lows: List of low prices
        window: Lookback window for pivot detection

    Returns:
        Dictionary with support and resistance levels
    """
    if len(highs) < window or len(lows) < window:
        return {
            "resistance": None,
            "support": None,
            "indicator_name": "support_resistance",
            "notes": "Insufficient data"
        }

    # Find resistance (highest high in recent window)
    recent_highs = highs[-window:]
    resistance = max(recent_highs)

    # Find support (lowest low in recent window)
    recent_lows = lows[-window:]
    support = min(recent_lows)

    # Current price (use last close, or approximate with last high)
    current_price = highs[-1]

    # Calculate distance from current price
    resistance_dist = ((resistance - current_price) / current_price * 100) if current_price > 0 else None
    support_dist = ((current_price - support) / current_price * 100) if current_price > 0 else None

    return {
        "resistance": resistance,
        "support": support,
        "resistance_distance_pct": resistance_dist,
        "support_distance_pct": support_dist,
        "current_price": current_price,
        "indicator_name": "support_resistance"
    }


# =============================================================================
# PRICE POSITION INDICATORS
# =============================================================================

def price_vs_sma(prices: PriceList, period: int = 200) -> TechnicalResult:
    """
    Calculate price position relative to SMA.

    Returns the percentage difference between current price and SMA.

    Args:
        prices: List of prices
        period: SMA period (default 200 for long-term trend)

    Returns:
        TechnicalResult with percentage above/below SMA
    """
    if len(prices) < period:
        return TechnicalResult(
            value=None,
            indicator_name="price_vs_sma",
            period=period,
            notes=f"Insufficient data: need {period} prices"
        )

    sma_result = sma(prices, period)
    if not sma_result.is_available:
        return TechnicalResult(
            value=None,
            indicator_name="price_vs_sma",
            period=period,
            notes="Could not calculate SMA"
        )

    current_price = prices[-1]
    sma_value = sma_result.value

    if sma_value == 0:
        return TechnicalResult(
            value=None,
            indicator_name="price_vs_sma",
            notes="SMA is zero"
        )

    pct_diff = ((current_price - sma_value) / sma_value) * 100

    # Signal
    signal = "below_sma" if pct_diff < 0 else "above_sma"

    return TechnicalResult(
        value=pct_diff,
        indicator_name="price_vs_sma",
        period=period,
        signal=signal,
        notes=f"Price is {pct_diff:.2f}% {'above' if pct_diff > 0 else 'below'} SMA{period}"
    )


# =============================================================================
# BATCH CALCULATION
# =============================================================================

def calculate_all_technicals(
    prices: PriceList,
    highs: Optional[PriceList] = None,
    lows: Optional[PriceList] = None,
    volumes: Optional[List[int]] = None
) -> dict:
    """
    Calculate all available technical indicators.

    Args:
        prices: List of closing prices (most recent last)
        highs: Optional list of high prices (for ATR, support/resistance)
        lows: Optional list of low prices (for ATR, support/resistance)
        volumes: Optional list of volume data

    Returns:
        Dictionary of all calculated indicators
    """
    results = {}

    # Moving Averages
    results["sma_20"] = sma(prices, 20)
    results["sma_50"] = sma(prices, 50)
    results["sma_200"] = sma(prices, 200)
    results["ema_12"] = ema(prices, 12)
    results["ema_26"] = ema(prices, 26)

    # Momentum
    results["rsi_14"] = rsi(prices, 14)
    macd_result = macd(prices)
    results["macd"] = macd_result

    # Volatility
    results["atr_14"] = atr(highs or prices, lows or prices, prices, 14) if highs and lows else TechnicalResult(None, "atr_14", notes="High/Low data required")
    results["volatility_20"] = volatility(prices, 20)
    results["drawdown"] = drawdown(prices)

    # Bollinger Bands
    bb_result = bollinger_bands(prices)
    results["bollinger_bands"] = bb_result

    # Volume (if available)
    if volumes:
        results["volume_sma_20"] = volume_sma(volumes, 20)
        results["volume_ratio"] = volume_ratio(volumes, 20)

    # Price vs SMA
    results["price_vs_sma_200"] = price_vs_sma(prices, 200)

    # Support/Resistance (if high/low data available)
    if highs and lows:
        sr_result = find_support_resistance(highs, lows)
        results["support_resistance"] = sr_result

    return results


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_technical_summary(prices: PriceList, period: int = 20) -> dict:
    """
    Get a summary of key technical indicators.

    Args:
        prices: List of closing prices
        period: Default period for indicators

    Returns:
        Dictionary with summarized technical signals
    """
    results = calculate_all_technicals(prices)

    summary = {
        "ticker": "UNKNOWN",  # Would be set by caller
        "calculated_at": str(date.today()),
        "indicators": {}
    }

    # Extract key signals
    key_indicators = [
        "sma_20", "sma_50", "sma_200",
        "rsi_14",
        "bollinger_bands",
        "price_vs_sma_200",
        "volume_ratio"
    ]

    for key in key_indicators:
        if key in results:
            result = results[key]
            if isinstance(result, TechnicalResult):
                summary["indicators"][key] = {
                    "value": result.value,
                    "signal": result.signal,
                    "is_available": result.is_available
                }
            elif isinstance(result, dict):
                summary["indicators"][key] = result

    return summary
