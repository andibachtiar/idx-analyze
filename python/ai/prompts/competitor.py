"""Competitor Analysis Prompt Integration (Phase 21)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class MoatSource:
    """A source of economic moat."""
    name: str  # Network Effects, Cost Advantage, Intangible Assets, Switching Costs, Efficient Scale
    strength: str  # Strong, Moderate, Weak, None
    description: str = ""


@dataclass
class FiveForcesScore:
    """Porter's Five Forces assessment."""
    competitive_rivalry: int = 3  # 1-5
    new_entrant_threat: int = 3
    supplier_power: int = 3
    buyer_power: int = 3
    substitute_threat: int = 3

    @property
    def industry_attractiveness(self) -> float:
        return sum([
            self.competitive_rivalry,
            6 - self.new_entrant_threat,
            6 - self.supplier_power,
            6 - self.buyer_power,
            6 - self.substitute_threat,
        ]) / 5.0


@dataclass
class CompetitorBenchmark:
    """Comparison against a single competitor."""
    ticker: str
    revenue_growth_3yr: float = 0.0
    gross_margin: float = 0.0
    operating_margin: float = 0.0
    roic: float = 0.0
    market_share: float = 0.0


@dataclass
class CompetitorAnalysisResult:
    """Complete competitor analysis result."""
    ticker: str
    company_name: str = ""
    moat_width: str = "Narrow"  # Wide, Narrow, None, At Risk
    moat_trend: str = "Stable"  # Widening, Stable, Narrowing
    moat_score: float = 5.0
    five_forces: FiveForcesScore = field(default_factory=FiveForcesScore)
    market_share: float = 0.0
    market_share_trend: str = "Stable"
    competitors: List[CompetitorBenchmark] = field(default_factory=list)
    pricing_power: str = "Moderate"
    innovation_position: str = "Neutral"
    overall_signal: str = "NEUTRAL"
    confidence: str = "MEDIUM"
    score: float = 5.0
    action: str = "HOLD"
    analysis_date: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "moat_width": self.moat_width,
            "moat_trend": self.moat_trend,
            "moat_score": self.moat_score,
            "industry_attractiveness": round(self.five_forces.industry_attractiveness, 1),
            "market_share": self.market_share,
            "overall_signal": self.overall_signal,
            "score": self.score,
            "action": self.action,
        }


def analyze_competitor_position(
    ticker: str,
    company_name: str = "",
    moat_width: str = "Narrow",
    moat_score: float = 5.0,
    market_share: float = 0.0,
    num_competitors: int = 3,
) -> CompetitorAnalysisResult:
    """Analyze competitive position for a ticker."""
    # Determine signal based on moat score
    if moat_score >= 7.0:
        signal, action, confidence = "BULLISH", "BUY", "HIGH"
    elif moat_score >= 5.0:
        signal, action, confidence = "NEUTRAL", "HOLD", "MEDIUM"
    else:
        signal, action, confidence = "BEARISH", "SELL", "MEDIUM"

    # Generate sample competitors (in production, these would come from real data)
    competitors = []
    for i in range(num_competitors):
        competitors.append(CompetitorBenchmark(
            ticker=f"COMP{i+1}",
            revenue_growth_3yr=0.08 + i * 0.02,
            gross_margin=0.40 + i * 0.05,
            operating_margin=0.15 + i * 0.03,
            roic=0.12 + i * 0.02,
            market_share=0.15 - i * 0.03,
        ))

    return CompetitorAnalysisResult(
        ticker=ticker,
        company_name=company_name or ticker,
        moat_width=moat_width,
        moat_score=moat_score,
        market_share=market_share,
        five_forces=FiveForcesScore(),
        competitors=competitors,
        overall_signal=signal,
        score=moat_score,
        action=action,
        confidence=confidence,
        analysis_date=datetime.now().strftime("%Y-%m-%d"),
    )


def generate_competitor_prompt(
    ticker: str,
    result: CompetitorAnalysisResult,
) -> str:
    """Generate prompt for LLM-based competitor analysis."""
    lines = [
        f"# Competitor Analysis — {ticker} ({result.company_name})",
        f"",
        f"## Moat Assessment",
        f"- Moat Width: {result.moat_width}",
        f"- Moat Trend: {result.moat_trend}",
        f"- Moat Score: {result.moat_score:.1f}/10",
        f"",
        f"## Industry Attractiveness",
        f"- Five Forces Score: {result.five_forces.industry_attractiveness:.1f}/5",
        f"",
        f"## Market Position",
        f"- Market Share: {result.market_share:.1%}",
        f"- Trend: {result.market_share_trend}",
        f"",
        f"## Competitive Benchmarking",
    ]

    for comp in result.competitors[:3]:
        lines.extend([
            f"- **{comp.ticker}**: Rev Growth {comp.revenue_growth_3yr:.1%}, Gross Margin {comp.gross_margin:.1%}, ROIC {comp.roic:.1%}",
        ])

    lines.extend([
        f"",
        f"## Analysis Request",
        f"Provide detailed competitive analysis including:",
        f"1. Moat source identification and durability assessment",
        f"2. Porter's Five Forces deep dive with scoring",
        f"3. Market share trend analysis",
        f"4. Competitive positioning vs. top peers",
        f"5. Pricing power assessment",
        f"6. Innovation and disruption risk",
        f"7. Investment implications based on moat assessment",
    ])

    return "\n".join(lines)
