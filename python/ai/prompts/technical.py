"""
Technical Analysis Prompt Integration (Phase 17).

Extends the existing technical analysis engine with LLM-powered
interpretation of chart patterns, moving averages, and trading signals
as specified in prompts/technical-analysis.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from analysis.technical import TechnicalResult

# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class MACDResult:
    """MACD indicator result."""
    macd_line: float
    signal_line: float
    histogram: float
    signal: str  # "bullish", "bearish", "neutral"


@dataclass
class BollingerBandResult:
    """Bollinger Bands result."""
    upper: float
    middle: float
    lower: float
    percent_b: float  # Position within bands
    width: float  # Band width as percentage


@dataclass
class MovingAverageSignal:
    """MA crossover signal."""
    ma_type: str  # "golden_cross", "death_cross", "price_above", "price_below"
    fast_ma: float
    slow_ma: float
    current_price: float
    distance_pct: float
    days_since_crossover: int


@dataclass
class IchimokuResult:
    """Ichimoku Cloud analysis result."""
    tenkan_sen: float
    kijun_sen: float
    senkou_span_a: float
    senkou_span_b: float
    chikou_span: float
    price_vs_cloud: str  # "above", "below", "inside"
    cloud_color: str  # "green", "red", "grey"
    tk_cross: str  # "bullish", "bearish", "none"
    bullish_signals: int
    bearish_signals: int


@dataclass
class TechnicalAnalysisResult:
    """Complete technical analysis result."""
    ticker: str
    analysis_date: str
    current_price: float
    trend: str  # "bullish", "bearish", "sideways"
    trend_strength: str  # "strong", "moderate", "weak"

    # MA Analysis
    ma_analysis: Dict[str, MovingAverageSignal]
    ma_stack_direction: str  # "bullish", "bearish", "mixed"

    # RSI
    rsi_14: Optional[float]
    rsi_signal: str  # "overbought", "oversold", "neutral"

    # MACD
    macd: Optional[MACDResult]

    # Bollinger Bands
    bollinger_bands: Optional[BollingerBandResult]

    # Volume
    volume_ratio: Optional[float]
    volume_trend: str  # "increasing", "decreasing", "stable"

    # Volatility
    atr_14: Optional[float]
    volatility_percent: Optional[float]

    # Support/Resistance
    support_levels: List[float]
    resistance_levels: List[float]

    # Overall Signal
    overall_signal: str  # "bullish", "bearish", "neutral"
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    score: float  # 0-10 scale
    horizon: str  # "SHORT", "MEDIUM", "LONG-TERM"
    action: str  # "BUY", "HOLD", "SELL"
    conviction: str  # "STRONG", "MODERATE", "WEAK"

    # Recommendations
    entry_price: Optional[float]
    target_price: Optional[float]
    stop_loss: Optional[float]
    risk_reward_ratio: Optional[float]

    # Notes
    key_observations: List[str]
    risks: List[str]
    recommendations: List[str]


# =============================================================================
# PROMPT GENERATION
# =============================================================================

def generate_technical_prompt(
    ticker: str,
    current_price: float,
    technical_data: Dict[str, Any],
) -> str:
    """
    Generate a prompt for LLM-based technical analysis interpretation.

    Args:
        ticker: Stock ticker symbol
        current_price: Current stock price
        technical_data: Technical indicators data from analysis engine

    Returns:
        Formatted prompt string for LLM
    """
    date_str = datetime.now().strftime("%Y-%m-%d")

    # Extract key indicators
    ma_data = technical_data.get("indicators", {}).get("sma_200", {})
    rsi_data = technical_data.get("indicators", {}).get("rsi_14", {})
    macd_data = technical_data.get("indicators", {}).get("macd", {})
    bb_data = technical_data.get("indicators", {}).get("bollinger_bands", {})

    # Build the prompt
    prompt = f"""# Technical Analysis — {ticker}
Date: {date_str}
Current Price: ${current_price:,.2f}
Data Source: Internal calculation engine

## ⚠️ Data Verification Required

Before proceeding with this analysis, verify the following:
1. Current price matches live market data
2. All technical indicators are calculated from actual price history
3. No data anomalies or outliers present

> ⚠️ **Live data unavailable.** The following analysis uses calculated estimates which may be significantly out of date. Verify all prices and metrics before making any decisions.

---

## Moving Average Analysis

### MA Values:
"""

    # MA table
    for period in [20, 50, 100, 200]:
        sma_key = f"sma_{period}"
        if sma_key in technical_data.get("indicators", {}):
            val = technical_data["indicators"][sma_key].get("value", 0)
            if val:
                diff_pct = ((current_price - val) / val) * 100 if val else 0
                position = "ABOVE" if current_price > val else "BELOW"
                prompt += f"- MA{period}: ${val:,.2f} ({position}, {diff_pct:+.2f}%)\n"

    prompt += f"""

### MA Stack Analysis:
"""

    # Determine MA stack direction
    sma_20 = technical_data.get("indicators", {}).get("sma_20", {})
    sma_50 = technical_data.get("indicators", {}).get("sma_50", {})
    sma_200 = technical_data.get("indicators", {}).get("sma_200", {})

    ma_values = []
    if sma_20.get("value"):
        ma_values.append(("MA20", sma_20["value"]))
    if sma_50.get("value"):
        ma_values.append(("MA50", sma_50["value"]))
    if sma_200.get("value"):
        ma_values.append(("MA200", sma_200["value"]))

    if len(ma_values) >= 3:
        values = [v[1] for v in ma_values]
        if values == sorted(values, reverse=True):
            prompt += "- MA Stack Direction: BULLISH (shorter MAs above longer MAs)\n"
        elif values == sorted(values):
            prompt += "- MA Stack Direction: BEARISH (longer MAs above shorter MAs)\n"
        else:
            prompt += "- MA Stack Direction: MIXED (inverted or disordered MAs)\n"

    prompt += f"""

## Technical Indicators Summary

| Indicator | Value | Signal |
|-----------|-------|--------|
"""

    # Add indicator summary
    if rsi_data.get("value"):
        rsi_val = rsi_data["value"]
        rsi_signal = "overbought" if rsi_val > 70 else "oversold" if rsi_val < 30 else "neutral"
        prompt += f"| RSI(14) | {rsi_val:.2f} | {rsi_signal} |\n"

    if macd_data.get("macd_line") is not None:
        macd_signal = "bullish" if (macd_data.get("histogram", 0) or 0) > 0 else "bearish"
        prompt += f"| MACD | Line: {macd_data['macd_line']:.4f} | {macd_signal} |\n"

    if bb_data.get("upper"):
        prompt += f"| Bollinger | Upper: ${bb_data['upper']:.2f} | Middle: ${bb_data['middle']:.2f} | Lower: ${bb_data['lower']:.2f} |\n"

    prompt += f"""

## Analysis Request

Based on the technical data above, provide a comprehensive technical analysis including:

1. **Trend Analysis**
   - Primary trend identification (uptrend, downtrend, sideways)
   - Trend strength assessment
   - Key support and resistance levels

2. **Moving Average Interpretation**
   - Current MA positions relative to price
   - Recent crossovers (golden cross/death cross)
   - MA stack alignment assessment

3. **Indicator Signals**
   - RSI interpretation and potential reversals
   - MACD momentum analysis
   - Bollinger Bands positioning and squeeze potential
   - Volume confirmation analysis

4. **Price Levels**
   - Key support zones
   - Key resistance zones
   - Fibonacci retracement levels (if applicable)

5. **Trading Recommendations**
   - Entry point suggestions
   - Target prices
   - Stop-loss levels
   - Risk/reward ratio

6. **Risk Assessment**
   - Key technical risks
   - Invalidations scenarios
   - Time horizon considerations

Format as a structured technical report with clear BUY/HOLD/SELL recommendation.
"""

    return prompt


def generate_trading_recommendation(
    ticker: str,
    current_price: float,
    technical_result: TechnicalAnalysisResult,
) -> str:
    """
    Generate a trading recommendation based on technical analysis.

    Args:
        ticker: Stock ticker symbol
        current_price: Current stock price
        technical_result: Complete technical analysis result

    Returns:
        Trading recommendation string
    """
    action = technical_result.action
    conviction = technical_result.conviction

    if action == "BUY":
        entry = f"${technical_result.entry_price:.2f}" if technical_result.entry_price else "Market"
        target = f"${technical_result.target_price:.2f}" if technical_result.target_price else "N/A"
        stop = f"${technical_result.stop_loss:.2f}" if technical_result.stop_loss else "N/A"
        rr = f"{technical_result.risk_reward_ratio:.1f}" if technical_result.risk_reward_ratio else "N/A"
        return f"""📈 STRONG BUY SIGNAL — {ticker}

{conviction} conviction signal detected.
- Entry: {entry}
- Target: {target}
- Stop Loss: {stop}
- Risk/Reward: 1:{rr}

Key technical factors supporting this signal:
{chr(10).join('- ' + obs for obs in technical_result.key_observations[:3])}

⚠️ Invalidation conditions:
{chr(10).join('• ' + risk for risk in technical_result.risks[:2])}

Horizon: {technical_result.horizon}
Confidence: {technical_result.confidence}
Score: {technical_result.score}/10"""

    elif action == "SELL":
        target = f"${technical_result.target_price:.2f}" if technical_result.target_price else "N/A"
        stop = f"${technical_result.stop_loss:.2f}" if technical_result.stop_loss else "N/A"
        rr = f"{technical_result.risk_reward_ratio:.1f}" if technical_result.risk_reward_ratio else "N/A"
        return f"""📉 STRONG SELL SIGNAL — {ticker}

{conviction} conviction sell signal detected.
- Consider exiting or shorting at ${current_price:.2f}
- Target: {target}
- Stop Loss: {stop}
- Risk/Reward: 1:{rr}

Key bearish factors:
{chr(10).join('- ' + obs for obs in technical_result.key_observations[:3])}

⚠️ Reversal conditions (would invalidate bearish thesis):
{chr(10).join('• ' + risk for risk in technical_result.risks[:2])}

 horison: {technical_result.horizon}
 confidence: {technical_result.confidence}
 score: {technical_result.score}/10"""

    else:  # HOLD
        # Handle empty support/resistance lists
        if technical_result.support_levels:
            support_str = f"${min(technical_result.support_levels):.2f}"
        else:
            support_str = "N/A"
        if technical_result.resistance_levels:
            resistance_str = f"${max(technical_result.resistance_levels):.2f}"
        else:
            resistance_str = "N/A"

        return f"""⏸️ HOLD SIGNAL — {ticker}

Current position: ${current_price:.2f}
No strong directional signal detected.

Key observations:
{chr(10).join('- ' + obs for obs in technical_result.key_observations[:3])}

Consider:
• Waiting for clearer technical signals
• Monitoring key levels: support {support_str}, resistance {resistance_str}
• Reviewing on next earnings release or major price movement

Horizon: {technical_result.horizon}
Confidence: {technical_result.confidence}
Score: {technical_result.score}/10"""


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

def analyze_stock_technicals(
    ticker: str,
    prices: List[float],
    volumes: Optional[List[int]] = None,
    highs: Optional[List[float]] = None,
    lows: Optional[List[float]] = None,
    use_llm: bool = False,
    llm_client=None,
) -> TechnicalAnalysisResult:
    """
    Perform comprehensive technical analysis with optional LLM interpretation.

    Args:
        ticker: Stock ticker symbol
        prices: List of closing prices (most recent last)
        volumes: Optional list of trading volumes
        highs: Optional list of high prices
        lows: Optional list of low prices
        use_llm: Whether to use LLM for enhanced interpretation
        llm_client: Optional LLMClient instance

    Returns:
        TechnicalAnalysisResult with complete technical analysis
    """
    from analysis.technical import (
        calculate_all_technicals,
        get_technical_summary,
    )

    # Run deterministic technical analysis
    results = calculate_all_technicals(prices, volumes=volumes, highs=highs, lows=lows)
    summary = get_technical_summary(prices)

    # Build result object
    result = TechnicalAnalysisResult(
        ticker=ticker,
        analysis_date=datetime.now().isoformat(),
        current_price=prices[-1] if prices else 0,
        trend="neutral",
        trend_strength="weak",
        ma_analysis={},
        ma_stack_direction="mixed",
        rsi_14=None,
        rsi_signal="neutral",
        macd=None,
        bollinger_bands=None,
        volume_ratio=None,
        volume_trend="stable",
        atr_14=None,
        volatility_percent=None,
        support_levels=[],
        resistance_levels=[],
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
        key_observations=[],
        risks=[],
        recommendations=[],
    )

    # Extract MA signals
    if "sma_20" in results and results["sma_20"].is_available:
        result.ma_analysis["ma20"] = MovingAverageSignal(
            ma_type="price_above",
            fast_ma=results["sma_20"].value,
            slow_ma=results.get("sma_50", TechnicalResult(None, "sma_50")).value or 0,
            current_price=prices[-1],
            distance_pct=((prices[-1] - results["sma_20"].value) / results["sma_20"].value) * 100,
            days_since_crossover=0,
        )

    # RSI
    if "rsi_14" in results and results["rsi_14"].is_available:
        result.rsi_14 = results["rsi_14"].value
        result.rsi_signal = results["rsi_14"].signal

    # MACD
    if "macd" in results:
        macd_data = results["macd"]
        result.macd = MACDResult(
            macd_line=macd_data.get("macd_line"),
            signal_line=macd_data.get("signal_line"),
            histogram=macd_data.get("histogram"),
            signal=macd_data.get("signal", "neutral"),
        )

    # Bollinger Bands
    if "bollinger_bands" in results:
        bb = results["bollinger_bands"]
        result.bollinger_bands = BollingerBandResult(
            upper=bb.get("upper"),
            middle=bb.get("middle"),
            lower=bb.get("lower"),
            percent_b=bb.get("percent_b"),
            width=bb.get("width"),
        )

    # Volume ratio
    if "volume_ratio" in results and results["volume_ratio"].is_available:
        result.volume_ratio = results["volume_ratio"].value
        result.volume_trend = "increasing" if result.volume_ratio > 1.2 else "decreasing" if result.volume_ratio < 0.8 else "stable"

    # ATR
    if "atr_14" in results and results["atr_14"].is_available:
        result.atr_14 = results["atr_14"].value
        result.volatility_percent = (result.atr_14 / prices[-1]) * 100 if prices[-1] else None

    # Support/Resistance
    if "support_resistance" in results:
        sr = results["support_resistance"]
        result.support_levels = [l["level"] for l in sr.get("supports", [])]
        result.resistance_levels = [l["level"] for l in sr.get("resistances", [])]

    # Calculate overall signal with trend context
    bullish_count = 0
    bearish_count = 0

    # Determine primary trend from moving averages
    has_bullish_ma = False
    has_bearish_ma = False

    if "sma_20" in results and results["sma_20"].is_available and prices:
        if prices[-1] > results["sma_20"].value:
            has_bullish_ma = True
        elif prices[-1] < results["sma_20"].value:
            has_bearish_ma = True

    # Price vs SMA20 (primary signal)
    if has_bullish_ma:
        bullish_count += 1
    elif has_bearish_ma:
        bearish_count += 1

    # MA Stack Alignment - adds signal when MAs are properly aligned
    ma_values = []
    for period in [20, 50, 200]:
        key = f"sma_{period}"
        if key in results and results[key].is_available and results[key].value:
            ma_values.append((period, results[key].value))

    if len(ma_values) >= 3:
        # Check if shorter MAs are above longer MAs (bullish stack)
        ma_sorted = sorted(ma_values, key=lambda x: x[0])
        ma_vals = [v[1] for v in ma_sorted]
        if ma_vals == sorted(ma_vals, reverse=True):
            # Bullish MA stack (20 > 50 > 200)
            bullish_count += 1
        elif ma_vals == sorted(ma_vals):
            # Bearish MA stack (200 > 50 > 20)
            bearish_count += 1

    # RSI - only count as reversal if contrary to trend
    if result.rsi_signal == "oversold":
        if not has_bearish_ma:  # Don't double-count in downtrend
            bullish_count += 1
    elif result.rsi_signal == "overbought":
        if not has_bullish_ma:  # Don't double-count in uptrend
            bearish_count += 1

    # MACD signal
    if result.macd:
        if result.macd.signal == "bullish":
            bullish_count += 1
        elif result.macd.signal == "bearish":
            bearish_count += 1

    # Bollinger Bands - only count extremes if contrary to trend
    if result.bollinger_bands and result.bollinger_bands.percent_b is not None:
        if result.bollinger_bands.percent_b < 0.2:
            if not has_bearish_ma:  # Don't double-count in downtrend
                bullish_count += 1
        elif result.bollinger_bands.percent_b > 0.8:
            if not has_bullish_ma:  # Don't double-count in uptrend
                bearish_count += 1

    # Determine trend
    if bullish_count >= 2:
        result.overall_signal = "bullish"
        result.trend = "bullish"
    elif bearish_count >= 2:
        result.overall_signal = "bearish"
        result.trend = "bearish"
    else:
        result.overall_signal = "neutral"
        result.trend = "sideways"

    # Calculate score (0-10)
    result.score = max(0, min(10, 5 + (bullish_count - bearish_count) * 1.5))

    # Set action and conviction
    if result.score >= 7:
        result.action = "BUY"
        result.conviction = "STRONG" if result.score >= 8 else "MODERATE"
    elif result.score <= 3:
        result.action = "SELL"
        result.conviction = "STRONG" if result.score <= 2 else "MODERATE"
    else:
        result.action = "HOLD"
        result.conviction = "MODERATE"

    # Calculate confidence based on available indicators and data sufficiency
    total_indicators = sum([
        1 if result.rsi_14 else 0,
        1 if result.macd else 0,
        1 if result.bollinger_bands else 0,
        1 if result.volume_ratio else 0,
    ])

    # Require sufficient data for confident signals
    if len(prices) < 50:
        result.confidence = "LOW"
    elif total_indicators >= 3:
        result.confidence = "HIGH"
    elif total_indicators >= 2:
        result.confidence = "MEDIUM"
    else:
        result.confidence = "LOW"

    # Generate key observations
    current_price_val = prices[-1] if prices else 0
    result.key_observations = [
        f"Current price: ${current_price_val:,.2f}",
        f"RSI(14): {result.rsi_14:.2f}" if result.rsi_14 else "RSI(14): N/A",
        f"MACD: {result.macd.signal}" if result.macd else "MACD: N/A",
        f"Trend: {result.trend}",
        f"Volume ratio: {result.volume_ratio:.2f}" if result.volume_ratio else "Volume: N/A",
    ]

    # Generate risks
    result.risks = [
        "Market-wide volatility could override technical signals",
        "Low volume periods may produce false breakouts",
        "Major news events can invalidate technical analysis",
    ]

    # Generate recommendations
    current_price_val = prices[-1] if prices else 0
    if result.action == "BUY":
        result.recommendations = [
            f"Consider entering near ${current_price_val:,.2f}",
            f"Set stop-loss at ${min(result.support_levels + [current_price_val * 0.95]):,.2f}" if result.support_levels or current_price_val else "Set stop-loss below recent support",
            f"Target ${max(result.resistance_levels + [current_price_val * 1.10]):,.2f}" if result.resistance_levels or current_price_val else "Target above recent resistance",
        ]
    elif result.action == "SELL":
        result.recommendations = [
            "Consider reducing position or exiting",
            "Set protective stop above recent resistance",
            "Wait for reversal confirmation before re-entering",
        ]
    else:
        result.recommendations = [
            "Maintain current position",
            "Monitor key support/resistance levels",
            "Wait for clearer directional signal",
        ]

    # Generate LLM-enhanced analysis if requested
    if use_llm and llm_client:
        current_price_for_prompt = prices[-1] if prices else 0
        llm_result = llm_client.analyze_with_prompt(
            prompt=generate_technical_prompt(ticker, current_price_for_prompt, results),
            output_format="Structured technical analysis report with trading recommendation",
        )
        result.llm_interpretation = llm_result.get("content")

    return result


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_technical_analysis_with_llm(
    ticker: str,
    prices: List[float],
    volumes: Optional[List[int]] = None,
    highs: Optional[List[float]] = None,
    lows: Optional[List[float]] = None,
    llm_client=None,
) -> Dict[str, Any]:
    """
    Get technical analysis with LLM interpretation.

    Args:
        ticker: Stock ticker symbol
        prices: List of closing prices (most recent last)
        volumes: Optional list of trading volumes
        highs: Optional list of high prices
        lows: Optional list of low prices
        llm_client: Optional LLMClient instance

    Returns:
        Dictionary with complete technical analysis and LLM interpretation
    """
    result = analyze_stock_technicals(
        ticker=ticker,
        prices=prices,
        volumes=volumes,
        highs=highs,
        lows=lows,
        use_llm=True,
        llm_client=llm_client,
    )

    return {
        "ticker": result.ticker,
        "analysis_date": result.analysis_date,
        "current_price": result.current_price,
        "trend": result.trend,
        "trend_strength": result.trend_strength,
        "overall_signal": result.overall_signal,
        "confidence": result.confidence,
        "score": result.score,
        "action": result.action,
        "conviction": result.conviction,
        "horizon": result.horizon,
        "entry_price": result.entry_price,
        "target_price": result.target_price,
        "stop_loss": result.stop_loss,
        "risk_reward_ratio": result.risk_reward_ratio,
        "key_observations": result.key_observations,
        "risks": result.risks,
        "recommendations": result.recommendations,
        "llm_interpretation": getattr(result, 'llm_interpretation', None),
    }
