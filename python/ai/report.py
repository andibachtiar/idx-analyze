"""
Report generation utilities for AI Research Analyst (Phase 11).

Handles formatting and structuring of investment research reports.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional


class ResearchReport:
    """
    Structured investment research report.

    Contains all sections of a professional research report with
    proper citation and confidence tracking.
    """

    def __init__(
        self,
        ticker: str,
        question: str,
        executive_summary: str = "",
        business_quality: str = "",
        growth_analysis: str = "",
        profitability: str = "",
        financial_health: str = "",
        valuation: str = "",
        technical_position: str = "",
        recent_events: str = "",
        risks: str = "",
        bull_case: str = "",
        base_case: str = "",
        bear_case: str = "",
        conclusion: str = "",
        data_sources: Optional[List[str]] = None,
        confidence: float = 0.0,
        timestamp: Optional[datetime] = None,
    ):
        self.ticker = ticker.upper()
        self.question = question
        self.executive_summary = executive_summary
        self.business_quality = business_quality
        self.growth_analysis = growth_analysis
        self.profitability = profitability
        self.financial_health = financial_health
        self.valuation = valuation
        self.technical_position = technical_position
        self.recent_events = recent_events
        self.risks = risks
        self.bull_case = bull_case
        self.base_case = base_case
        self.bear_case = bear_case
        self.conclusion = conclusion
        self.data_sources = data_sources or []
        self.confidence = confidence
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return {
            "ticker": self.ticker,
            "question": self.question,
            "executive_summary": self.executive_summary,
            "business_quality": self.business_quality,
            "growth_analysis": self.growth_analysis,
            "profitability": self.profitability,
            "financial_health": self.financial_health,
            "valuation": self.valuation,
            "technical_position": self.technical_position,
            "recent_events": self.recent_events,
            "risks": self.risks,
            "bull_case": self.bull_case,
            "base_case": self.base_case,
            "bear_case": self.bear_case,
            "conclusion": self.conclusion,
            "data_sources": self.data_sources,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_markdown(self) -> str:
        """Convert report to markdown format."""
        return f"""# Investment Research Report: {self.ticker}

**Question:** {self.question}
**Timestamp:** {self.timestamp.strftime('%Y-%m-%d %H:%M')}
**Confidence:** {self.confidence:.1%}

---

## Executive Summary
{self.executive_summary}

## Business Quality
{self.business_quality}

## Growth Analysis
{self.growth_analysis}

## Profitability
{self.profitability}

## Financial Health
{self.financial_health}

## Valuation
{self.valuation}

## Technical Position
{self.technical_position}

## Recent Events & Catalysts
{self.recent_events}

## Risks
{self.risks}

## Bull Case
{self.bull_case}

## Base Case
{self.base_case}

## Bear Case
{self.bear_case}

## Conclusion
{self.conclusion}

---
**Data Sources:** {', '.join(self.data_sources) if self.data_sources else 'N/A'}
**Report Generated:** {self.timestamp.isoformat()}
"""

    def __repr__(self) -> str:
        return f"ResearchReport(ticker={self.ticker}, confidence={self.confidence:.1%})"


class ClaimTracker:
    """
    Track claims made in analysis and their supporting evidence.

    Helps distinguish between FACT, INTERPRETATION, ASSUMPTION, and SPECULATION.
    """

    def __init__(self):
        self.claims: List[Dict[str, Any]] = []

    def add_claim(
        self,
        claim: str,
        type_: str,
        evidence: Optional[str] = None,
        source: Optional[str] = None,
        confidence: float = 1.0,
    ):
        """
        Add a claim with its type and supporting evidence.

        Args:
            claim: The claim being made
            type_: One of "FACT", "INTERPRETATION", "ASSUMPTION", "SPECULATION"
            evidence: Supporting evidence or data point
            source: Source of the evidence
            confidence: Confidence level (0.0 to 1.0)
        """
        self.claims.append({
            "claim": claim,
            "type": type_,
            "evidence": evidence,
            "source": source,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
        })

    def get_claims_by_type(self, type_: str) -> List[Dict[str, Any]]:
        """Get all claims of a specific type."""
        return [c for c in self.claims if c["type"] == type_]

    def get_summary(self) -> Dict[str, int]:
        """Get count of claims by type."""
        summary = {"FACT": 0, "INTERPRETATION": 0, "ASSUMPTION": 0, "SPECULATION": 0}
        for claim in self.claims:
            if claim["type"] in summary:
                summary[claim["type"]] += 1
        summary["total_claims"] = len(self.claims)
        return summary

    def to_dict(self) -> Dict[str, Any]:
        """Convert claim tracker to dictionary."""
        return {
            "claims": self.claims,
            "summary": self.get_summary(),
            "total_claims": len(self.claims),
        }


def generate_report_sections(
    ticker: str,
    question: str,
    fundamental_data: Dict[str, Any],
    valuation_data: Dict[str, Any],
    technical_data: Dict[str, Any],
    historical_data: Dict[str, Any],
) -> Dict[str, str]:
    """
    Generate report sections from analyzed data.

    This is a template function - in production, this would call the LLM
    to generate the actual text content.
    """
    return {
        "executive_summary": f"Analysis of {ticker} based on user question: '{question}'",
        "business_quality": "Business quality analysis pending LLM integration.",
        "growth_analysis": "Growth analysis pending LLM integration.",
        "profitability": "Profitability analysis pending LLM integration.",
        "financial_health": "Financial health analysis pending LLM integration.",
        "valuation": "Valuation analysis pending LLM integration.",
        "technical_position": "Technical position analysis pending LLM integration.",
        "recent_events": "Recent events analysis pending LLM integration.",
        "risks": "Risk analysis pending LLM integration.",
        "bull_case": "Bull case analysis pending LLM integration.",
        "base_case": "Base case analysis pending LLM integration.",
        "bear_case": "Bear case analysis pending LLM integration.",
        "conclusion": "Conclusion pending LLM integration.",
    }
