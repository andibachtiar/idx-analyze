"""
Standard report templates for AI Research Analyst (Phase 12).

Defines the standardized structure for investment research reports
with clear separation of facts, interpretations, assumptions, and speculation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ClaimType(Enum):
    """Type of claim in a research report."""
    FACT = "FACT"
    INTERPRETATION = "INTERPRETATION"
    ASSUMPTION = "ASSUMPTION"
    SPECULATION = "SPECULATION"


@dataclass
class Claim:
    """
    A single claim in a research report.

    Each claim is tagged with its type to help distinguish
    between verified facts and speculative statements.
    """
    text: str
    claim_type: ClaimType
    evidence: Optional[str] = None
    source: Optional[str] = None
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert claim to dictionary."""
        return {
            "text": self.text,
            "type": self.claim_type.value,
            "evidence": self.evidence,
            "source": self.source,
            "confidence": self.confidence,
        }


@dataclass
class ReportSection:
    """
    A section of a research report.

    Contains claims with their types for transparent analysis.
    """
    title: str
    content: str = ""
    claims: List[Claim] = field(default_factory=list)
    sub_sections: Dict[str, "ReportSection"] = field(default_factory=dict)

    def add_claim(self, claim: Claim):
        """Add a claim to this section."""
        self.claims.append(claim)

    def add_subsection(self, title: str, section: "ReportSection"):
        """Add a subsection to this section."""
        self.sub_sections[title] = section

    def to_dict(self) -> Dict[str, Any]:
        """Convert section to dictionary."""
        result = {
            "title": self.title,
            "content": self.content,
            "claims": [c.to_dict() for c in self.claims],
        }
        if self.sub_sections:
            result["subsections"] = {
                title: sub.to_dict()
                for title, sub in self.sub_sections.items()
            }
        return result


@dataclass
class InvestmentReport:
    """
    Complete investment research report with structured claims.

    The report clearly separates facts from interpretations and
    tracks the confidence level of each claim.
    """
    ticker: str
    question: str
    generated_at: datetime = field(default_factory=datetime.now)
    data_sources: List[str] = field(default_factory=list)
    data_timestamp: Optional[str] = None

    # Main sections
    executive_summary: ReportSection = field(
        default_factory=lambda: ReportSection(title="Executive Summary")
    )
    business_quality: ReportSection = field(
        default_factory=lambda: ReportSection(title="Business Quality")
    )
    growth_analysis: ReportSection = field(
        default_factory=lambda: ReportSection(title="Revenue & Earnings Growth")
    )
    profitability: ReportSection = field(
        default_factory=lambda: ReportSection(title="Profitability")
    )
    balance_sheet: ReportSection = field(
        default_factory=lambda: ReportSection(title="Balance Sheet")
    )
    cash_flow: ReportSection = field(
        default_factory=lambda: ReportSection(title="Cash Flow")
    )
    valuation: ReportSection = field(
        default_factory=lambda: ReportSection(title="Valuation")
    )
    technical_position: ReportSection = field(
        default_factory=lambda: ReportSection(title="Technical Position")
    )
    ownership_relationships: ReportSection = field(
        default_factory=lambda: ReportSection(title="Ownership & Relationships")
    )
    recent_events: ReportSection = field(
        default_factory=lambda: ReportSection(title="Recent Events")
    )
    catalysts: ReportSection = field(
        default_factory=lambda: ReportSection(title="Catalysts")
    )
    risks: ReportSection = field(
        default_factory=lambda: ReportSection(title="Risks")
    )
    bull_case: ReportSection = field(
        default_factory=lambda: ReportSection(title="Bull Case")
    )
    base_case: ReportSection = field(
        default_factory=lambda: ReportSection(title="Base Case")
    )
    bear_case: ReportSection = field(
        default_factory=lambda: ReportSection(title="Bear Case")
    )
    conclusion: ReportSection = field(
        default_factory=lambda: ReportSection(title="Conclusion")
    )

    # Overall metrics
    confidence_score: float = 0.5
    overall_verdict: str = ""

    def add_fact(self, section: ReportSection, text: str, evidence: str = "", source: str = ""):
        """Add a factual claim to a section."""
        section.add_claim(Claim(
            text=text,
            claim_type=ClaimType.FACT,
            evidence=evidence,
            source=source,
            confidence=1.0,
        ))

    def add_interpretation(self, section: ReportSection, text: str, confidence: float = 0.7):
        """Add an interpretive claim to a section."""
        section.add_claim(Claim(
            text=text,
            claim_type=ClaimType.INTERPRETATION,
            confidence=confidence,
        ))

    def add_assumption(self, section: ReportSection, text: str, confidence: float = 0.5):
        """Add an assumed claim to a section."""
        section.add_claim(Claim(
            text=text,
            claim_type=ClaimType.ASSUMPTION,
            confidence=confidence,
        ))

    def add_speculation(self, section: ReportSection, text: str, confidence: float = 0.3):
        """Add a speculative claim to a section."""
        section.add_claim(Claim(
            text=text,
            claim_type=ClaimType.SPECULATION,
            confidence=confidence,
        ))

    def get_claims_by_type(self, claim_type: ClaimType) -> List[Claim]:
        """Get all claims of a specific type across the report."""
        all_claims = []
        for section in [
            self.executive_summary, self.business_quality, self.growth_analysis,
            self.profitability, self.balance_sheet, self.cash_flow, self.valuation,
            self.technical_position, self.ownership_relationships, self.recent_events,
            self.catalysts, self.risks, self.bull_case, self.base_case, self.bear_case,
            self.conclusion,
        ]:
            all_claims.extend([c for c in section.claims if c.claim_type == claim_type])
        return all_claims

    def get_summary_stats(self) -> Dict[str, int]:
        """Get summary statistics of claims by type."""
        stats = {
            "FACT": len(self.get_claims_by_type(ClaimType.FACT)),
            "INTERPRETATION": len(self.get_claims_by_type(ClaimType.INTERPRETATION)),
            "ASSUMPTION": len(self.get_claims_by_type(ClaimType.ASSUMPTION)),
            "SPECULATION": len(self.get_claims_by_type(ClaimType.SPECULATION)),
        }
        stats["total_claims"] = sum(stats.values())
        return stats

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "ticker": self.ticker,
            "question": self.question,
            "generated_at": self.generated_at.isoformat(),
            "data_sources": self.data_sources,
            "data_timestamp": self.data_timestamp,
            "confidence_score": self.confidence_score,
            "overall_verdict": self.overall_verdict,
            "claim_summary": self.get_summary_stats(),
            "sections": {
                "executive_summary": self.executive_summary.to_dict(),
                "business_quality": self.business_quality.to_dict(),
                "growth_analysis": self.growth_analysis.to_dict(),
                "profitability": self.profitability.to_dict(),
                "balance_sheet": self.balance_sheet.to_dict(),
                "cash_flow": self.cash_flow.to_dict(),
                "valuation": self.valuation.to_dict(),
                "technical_position": self.technical_position.to_dict(),
                "ownership_relationships": self.ownership_relationships.to_dict(),
                "recent_events": self.recent_events.to_dict(),
                "catalysts": self.catalysts.to_dict(),
                "risks": self.risks.to_dict(),
                "bull_case": self.bull_case.to_dict(),
                "base_case": self.base_case.to_dict(),
                "bear_case": self.bear_case.to_dict(),
                "conclusion": self.conclusion.to_dict(),
            },
        }

    def to_markdown(self) -> str:
        """Convert report to markdown format."""
        lines = [
            f"# Investment Research Report: {self.ticker}",
            f"",
            f"**Question:** {self.question}",
            f"**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M')}",
            f"**Confidence Score:** {self.confidence_score:.1%}",
            f"**Data Sources:** {', '.join(self.data_sources) if self.data_sources else 'N/A'}",
            f"",
            f"---",
            f"",
            f"## Claim Summary",
            f"",
            f"| Type | Count |",
            f"|------|-------|",
            f"| FACT | {self.get_summary_stats()['FACT']} |",
            f"| INTERPRETATION | {self.get_summary_stats()['INTERPRETATION']} |",
            f"| ASSUMPTION | {self.get_summary_stats()['ASSUMPTION']} |",
            f"| SPECULATION | {self.get_summary_stats()['SPECULATION']} |",
            f"",
            f"---",
            f"",
        ]

        # Add each section
        sections = [
            ("Executive Summary", self.executive_summary),
            ("Business Quality", self.business_quality),
            ("Revenue & Earnings Growth", self.growth_analysis),
            ("Profitability", self.profitability),
            ("Balance Sheet", self.balance_sheet),
            ("Cash Flow", self.cash_flow),
            ("Valuation", self.valuation),
            ("Technical Position", self.technical_position),
            ("Ownership & Relationships", self.ownership_relationships),
            ("Recent Events", self.recent_events),
            ("Catalysts", self.catalysts),
            ("Risks", self.risks),
            ("Bull Case", self.bull_case),
            ("Base Case", self.base_case),
            ("Bear Case", self.bear_case),
            ("Conclusion", self.conclusion),
        ]

        for title, section in sections:
            lines.append(f"## {title}")
            lines.append("")
            lines.append(section.content)
            lines.append("")

            # Add claims with type indicators
            if section.claims:
                lines.append("**Claims:**")
                lines.append("")
                for claim in section.claims:
                    type_indicator = {
                        ClaimType.FACT: "✅",
                        ClaimType.INTERPRETATION: "💭",
                        ClaimType.ASSUMPTION: "🔶",
                        ClaimType.SPECULATION: "🔮",
                    }.get(claim.claim_type, "⚪")

                    lines.append(f"- {type_indicator} **{claim.claim_type.value}** ({claim.confidence:.0%}): {claim.text}")
                    if claim.evidence:
                        lines.append(f"  - Evidence: {claim.evidence}")
                    if claim.source:
                        lines.append(f"  - Source: {claim.source}")
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"InvestmentReport(ticker={self.ticker}, confidence={self.confidence_score:.1%})"


# =============================================================================
# REPORT TEMPLATES
# =============================================================================

def create_standard_report(
    ticker: str,
    question: str,
    fundamental_data: Optional[Dict] = None,
    valuation_data: Optional[Dict] = None,
    technical_data: Optional[Dict] = None,
    historical_data: Optional[Dict] = None,
) -> InvestmentReport:
    """
    Create a standard investment report with given data.

    This is a factory function that creates a properly structured
    report with placeholder content that can be filled in by the LLM.
    """
    report = InvestmentReport(
        ticker=ticker,
        question=question,
        data_sources=[],
    )

    # Add structured content based on available data
    if fundamental_data:
        report.data_sources.append("fundamental_analysis")
        report.profitability.content = _format_fundamental_content(fundamental_data)

    if valuation_data:
        report.data_sources.append("valuation_analysis")
        report.valuation.content = _format_valuation_content(valuation_data)

    if technical_data:
        report.data_sources.append("technical_analysis")
        report.technical_position.content = _format_technical_content(technical_data)

    if historical_data:
        report.data_sources.append("historical_analysis")
        report.growth_analysis.content = _format_historical_content(historical_data)

    return report


def _format_fundamental_content(data: Dict) -> str:
    """Format fundamental analysis data into readable content."""
    lines = []

    # Profitability metrics
    if "profitability" in data:
        prof = data["profitability"]
        roe = prof.get("roe", {})
        roa = prof.get("roa", {})
        net_margin = prof.get("net_margin", {})

        lines.append("### Profitability Metrics")
        lines.append("")
        if roe.get("value"):
            lines.append(f"- **ROE:** {roe['value']:.2%}" if roe['value'] < 1 else f"- **ROE:** {roe['value']:.2f}")
        if roa.get("value"):
            lines.append(f"- **ROA:** {roa['value']:.2%}" if roa['value'] < 1 else f"- **ROA:** {roa['value']:.2f}")
        if net_margin.get("value"):
            lines.append(f"- **Net Margin:** {net_margin['value']:.2%}" if net_margin['value'] < 1 else f"- **Net Margin:** {net_margin['value']:.2f}")
        lines.append("")

    return "\n".join(lines) if lines else "Fundamental data not available."


def _format_valuation_content(data: Dict) -> str:
    """Format valuation analysis data into readable content."""
    lines = []

    if "valuations" in data:
        vals = data["valuations"]

        lines.append("### Valuation Metrics")
        lines.append("")
        if "pe_ratio" in vals and vals["pe_ratio"].get("value"):
            lines.append(f"- **P/E Ratio:** {vals['pe_ratio']['value']:.2f}")
        if "pb_ratio" in vals and vals["pb_ratio"].get("value"):
            lines.append(f"- **P/B Ratio:** {vals['pb_ratio']['value']:.2f}")
        if "ev_ebitda" in vals and vals["ev_ebitda"].get("value"):
            lines.append(f"- **EV/EBITDA:** {vals['ev_ebitda']['value']:.2f}")
        lines.append("")

        # Historical comparison
        if "historical_comparison" in data and data["historical_comparison"]:
            lines.append("### Historical Context")
            lines.append("")
            hist = data["historical_comparison"]
            if "pe_ratio" in hist and hist["pe_ratio"].get("percentile"):
                lines.append(f"- P/E percentile: {hist['pe_ratio']['percentile']:.0f}%")
            lines.append("")

    return "\n".join(lines) if lines else "Valuation data not available."


def _format_technical_content(data: Dict) -> str:
    """Format technical analysis data into readable content."""
    lines = []

    if "indicators" in data:
        inds = data["indicators"]

        lines.append("### Technical Indicators")
        lines.append("")

        # Moving averages
        for sma_key in ["sma_20", "sma_50", "sma_200"]:
            if sma_key in inds and inds[sma_key].get("value"):
                lines.append(f"- **{sma_key.upper()}** (SMA {sma_key[-2:]}): {inds[sma_key]['value']:.2f}")
        lines.append("")

        # RSI
        if "rsi_14" in inds and inds["rsi_14"].get("value"):
            rsi = inds["rsi_14"]["value"]
            signal = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
            lines.append(f"- **RSI (14):** {rsi:.2f} ({signal})")
        lines.append("")

        # Signals
        if "signals" in data and data["signals"]:
            lines.append("### Signals")
            lines.append("")
            for signal_name, signal_value in data["signals"].items():
                lines.append(f"- **{signal_name}:** {signal_value}")
            lines.append("")

    return "\n".join(lines) if lines else "Technical data not available."


def _format_historical_content(data: Dict) -> str:
    """Format historical analysis data into readable content."""
    lines = []

    if "growth" in data:
        growth = data["growth"]

        lines.append("### Growth Rates")
        lines.append("")

        for metric_name, metric_data in growth.items():
            if metric_data.get("value") is not None:
                value = metric_data["value"]
                if abs(value) < 1:
                    lines.append(f"- **{metric_name}:** {value:.2%}")
                else:
                    lines.append(f"- **{metric_name}:** {value:.2f}")
        lines.append("")

    if "trends" in data:
        trends = data["trends"]

        lines.append("### Trends")
        lines.append("")
        for metric_name, trend in trends.items():
            lines.append(f"- **{metric_name}:** {trend}")
        lines.append("")

    return "\n".join(lines) if lines else "Historical data not available."
