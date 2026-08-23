"""Institutional Ownership Analysis (Phase 22)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class InstitutionHolder:
    """A single institutional holder."""
    name: str
    type: str  # Index, Active, Hedge Fund, Pension, etc.
    shares_held: float = 0.0
    value_millions: float = 0.0
    pct_of_portfolio: float = 0.0
    pct_of_company: float = 0.0
    change_qoq: float = 0.0
    signal_strength: str = "Medium"


@dataclass
class OwnershipTrend:
    """Quarterly ownership trend."""
    quarter: str
    institutional_pct: float = 0.0
    num_holders: int = 0
    change_from_prior: float = 0.0


@dataclass
class PositionChange:
    """A position change event."""
    institution: str
    action: str  # New, Increased, Decreased, Eliminated
    shares: float = 0.0
    value_millions: float = 0.0
    change_pct: float = 0.0
    significance: str = "Medium"


@dataclass
class InstitutionalOwnershipResult:
    """Complete institutional ownership analysis."""
    ticker: str
    total_institutional_ownership: float = 0.0
    num_holders: int = 0
    total_value_millions: float = 0.0
    top_holders: List[InstitutionHolder] = field(default_factory=list)
    ownership_trends: List[OwnershipTrend] = field(default_factory=list)
    position_changes: List[PositionChange] = field(default_factory=list)
    smart_money_buyers: List[str] = field(default_factory=list)
    smart_money_sellers: List[str] = field(default_factory=list)
    concentration_top10: float = 0.0
    activist_holdings: List[str] = field(default_factory=list)
    overall_signal: str = "NEUTRAL"
    confidence: str = "MEDIUM"
    score: float = 5.0
    action: str = "HOLD"
    red_flags: List[str] = field(default_factory=list)
    positive_signals: List[str] = field(default_factory=list)
    analysis_date: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "institutional_ownership_pct": self.total_institutional_ownership,
            "num_holders": self.num_holders,
            "top10_concentration": self.concentration_top10,
            "overall_signal": self.overall_signal,
            "score": self.score,
            "action": self.action,
            "red_flags": self.red_flags,
            "positive_signals": self.positive_signals,
        }


def analyze_institutional_ownership(
    ticker: str,
    institutional_ownership_pct: float = 70.0,
    num_holders: int = 500,
    top10_concentration: float = 40.0,
) -> InstitutionalOwnershipResult:
    """Analyze institutional ownership for a ticker."""
    # Generate sample top holders
    top_holders = [
        InstitutionHolder(name="Vanguard Group", type="Index", shares_held=50000000,
                          value_millions=7500, pct_of_portfolio=0.8, pct_of_company=8.5,
                          change_qoq=2.1, signal_strength="Medium"),
        InstitutionHolder(name="BlackRock", type="Index", shares_held=42000000,
                          value_millions=6300, pct_of_portfolio=0.6, pct_of_company=7.2,
                          change_qoq=1.5, signal_strength="Medium"),
        InstitutionHolder(name="Fidelity", type="Active", shares_held=25000000,
                          value_millions=3750, pct_of_portfolio=2.1, pct_of_company=4.3,
                          change_qoq=15.2, signal_strength="High"),
    ]

    # Generate sample trends
    trends = [
        OwnershipTrend(quarter="Q4 2024", institutional_pct=73.2, num_holders=850, change_from_prior=1.5),
        OwnershipTrend(quarter="Q3 2024", institutional_pct=71.7, num_holders=832, change_from_prior=0.8),
        OwnershipTrend(quarter="Q2 2024", institutional_pct=70.9, num_holders=815, change_from_prior=-0.3),
        OwnershipTrend(quarter="Q1 2024", institutional_pct=71.2, num_holders=809, change_from_prior=2.1),
    ]

    # Determine signal based on trends
    if institutional_ownership_pct > 70 and top10_concentration < 50:
        signal, action, score = "BULLISH", "BUY", 7.0
    elif institutional_ownership_pct > 60:
        signal, action, score = "NEUTRAL", "HOLD", 5.5
    else:
        signal, action, score = "BEARISH", "SELL", 4.0

    return InstitutionalOwnershipResult(
        ticker=ticker,
        total_institutional_ownership=institutional_ownership_pct,
        num_holders=num_holders,
        top_holders=top_holders,
        ownership_trends=trends,
        concentration_top10=top10_concentration,
        overall_signal=signal,
        score=score,
        action=action,
        analysis_date=datetime.now().strftime("%Y-%m-%d"),
    )


def generate_institutional_ownership_prompt(
    ticker: str,
    result: InstitutionalOwnershipResult,
) -> str:
    """Generate prompt for LLM-based institutional ownership analysis."""
    lines = [
        f"# Institutional Ownership Analysis — {ticker}",
        f"",
        f"## Ownership Overview",
        f"- Institutional Ownership: {result.total_institutional_ownership:.1f}%",
        f"- Number of Holders: {result.num_holders}",
        f"- Top 10 Concentration: {result.concentration_top10:.1f}%",
        f"- Overall Signal: {result.overall_signal}",
        f"",
        f"## Ownership Trend (Last 4 Quarters)",
    ]

    for trend in result.ownership_trends:
        lines.append(f"- {trend.quarter}: {trend.institutional_ownership_pct:.1f}% ({trend.num_holders} holders)")

    lines.extend([
        f"",
        f"## Top Holders",
    ])

    for holder in result.top_holders[:5]:
        lines.extend([
            f"- **{holder.name}** ({holder.type}): {holder.pct_of_company:.1f}% of company",
            f"  - Change: {holder.change_qoq:+.1f}% | Signal: {holder.signal_strength}",
        ])

    lines.extend([
        f"",
        f"## Analysis Request",
        f"Provide comprehensive institutional ownership analysis including:",
        f"1. Trend interpretation and momentum",
        f"2. Smart money flow analysis",
        f"3. Ownership concentration risks",
        f"4. Activist investor identification",
        f"5. Red flags and warning signs",
        f"6. Investment implications",
    ])

    return "\n".join(lines)
