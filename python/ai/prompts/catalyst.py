"""Catalyst Calendar Prompt Integration (Phase 20)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


@dataclass
class CatalystEvent:
    """Represents a single catalyst event."""
    event_type: str  # earnings, fomc, cpi, product_launch, etc.
    title: str
    date: str
    probability: str  # High, Medium, Low
    bull_impact: float = 0.0
    bear_impact: float = 0.0
    net_bias: str = "Neutral"
    pre_event_action: str = "Hold"


@dataclass
class EarningsData:
    """Earnings-specific data."""
    next_earnings_date: str
    quarter: str
    eps_estimate: float = 0.0
    revenue_estimate: float = 0.0
    implied_move_pct: float = 0.0
    beat_rate_8q: float = 0.5
    historical_avg_move: float = 0.0


@dataclass
class MacroEventData:
    """Macro event data."""
    event_type: str  # fomc, cpi, npf
    date: str
    expectation: str
    stock_sensitivity: str  # High, Medium, Low
    direction: str  # Positive, Negative, Neutral


@dataclass
class CatalystCalendarResult:
    """Complete catalyst calendar analysis."""
    ticker: str
    look_back_days: int = 90
    events: List[CatalystEvent] = field(default_factory=list)
    earnings_data: Optional[EarningsData] = None
    macro_events: List[MacroEventData] = field(default_factory=list)
    overall_bias: str = "NEUTRAL"
    peak_risk_window: str = ""
    quietest_window: str = ""
    heat_map: Dict[str, str] = field(default_factory=dict)
    analysis_date: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "overall_bias": self.overall_bias,
            "num_events": len(self.events),
            "peak_risk_window": self.peak_risk_window,
            "events": [e.__dict__ for e in self.events],
        }


def analyze_catalyst_calendar(
    ticker: str,
    look_back_days: int = 90,
    focus: str = "all",
) -> CatalystCalendarResult:
    """Analyze catalyst calendar for a ticker."""
    today = datetime.now()
    end_date = today + timedelta(days=look_back_days)

    # Generate sample catalysts (in production, these would come from real data sources)
    events = []

    # Sample earnings event
    earnings_date = today + timedelta(days=45)
    events.append(CatalystEvent(
        event_type="earnings",
        title=f"{ticker} Q3 Earnings",
        date=earnings_date.strftime("%Y-%m-%d"),
        probability="High",
        bull_impact=5.0,
        bear_impact=-4.0,
        net_bias="Neutral",
        pre_event_action="Buy dip before",
    ))

    # Sample FOMC events
    for i in range(3):
        fomc_date = today + timedelta(days=30 + i * 40)
        events.append(CatalystEvent(
            event_type="fomc",
            title="FOMC Meeting",
            date=fomc_date.strftime("%Y-%m-%d"),
            probability="High",
            bull_impact=2.0,
            bear_impact=-2.0,
            net_bias="Neutral",
            pre_event_action="Hold",
        ))

    # Sample product launch
    product_date = today + timedelta(days=60)
    events.append(CatalystEvent(
        event_type="product_launch",
        title=f"{ticker} Product Launch",
        date=product_date.strftime("%Y-%m-%d"),
        probability="Medium",
        bull_impact=3.0,
        bear_impact=-1.0,
        net_bias="Bullish",
        pre_event_action="Buy ahead",
    ))

    # Determine overall bias
    bullish_count = sum(1 for e in events if e.net_bias == "Bullish")
    bearish_count = sum(1 for e in events if e.net_bias == "Bearish")

    if bullish_count > bearish_count:
        overall_bias = "BULLISH"
    elif bearish_count > bullish_count:
        overall_bias = "BEARISH"
    else:
        overall_bias = "NEUTRAL"

    # Find peak risk window
    peak_risk = "Next 30 days"
    quietest = "Days 60-90"

    return CatalystCalendarResult(
        ticker=ticker,
        look_back_days=look_back_days,
        events=events,
        overall_bias=overall_bias,
        peak_risk_window=peak_risk,
        quietest_window=quietest,
        analysis_date=datetime.now().strftime("%Y-%m-%d"),
    )


def generate_catalyst_prompt(
    ticker: str,
    result: CatalystCalendarResult,
) -> str:
    """Generate prompt for LLM-based catalyst analysis."""
    lines = [
        f"# Catalyst Calendar Analysis — {ticker}",
        f"",
        f"## Overview",
        f"- Look-ahead Window: {result.look_back_days} days",
        f"- Total Catalysts: {len(result.events)}",
        f"- Overall Bias: {result.overall_bias}",
        f"",
        f"## Catalyst Events",
    ]

    for event in result.events[:5]:  # Top 5 events
        lines.extend([
            f"- **{event.title}** ({event.date})",
            f"  - Probability: {event.probability}",
            f"  - Impact: {event.bull_impact:+.1f}% / {event.bear_impact:.1f}%",
            f"  - Action: {event.pre_event_action}",
        ])

    lines.extend([
        f"",
        f"## Risk Windows",
        f"- Peak Risk: {result.peak_risk_window}",
        f"- Quietest: {result.quietest_window}",
        f"",
        f"## Analysis Request",
        f"Provide detailed analysis of the catalyst landscape including:",
        f"1. Earnings expectations and historical performance",
        f"2. Macro event sensitivities",
        f"3. Positioning recommendations",
        f"4. Hedge strategies for binary events",
    ])

    return "\n".join(lines)
