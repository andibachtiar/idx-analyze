"""
Enhanced report generation for AI Research Analyst (Phase 12).

Provides improved report formatting with explicit fact/interpretation
separation and confidence tracking.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from ai.report_templates import (
    Claim,
    ClaimType,
    InvestmentReport,
    ReportSection,
    create_standard_report,
)


class ReportGenerator:
    """
    Generates structured investment research reports.

    Ensures clear separation between facts, interpretations,
    assumptions, and speculation.
    """

    def __init__(self):
        self.report: Optional[InvestmentReport] = None

    def create_report(
        self,
        ticker: str,
        question: str,
        fundamental_data: Optional[Dict] = None,
        valuation_data: Optional[Dict] = None,
        technical_data: Optional[Dict] = None,
        historical_data: Optional[Dict] = None,
    ) -> InvestmentReport:
        """
        Create a new investment report with the given data.

        Args:
            ticker: Stock ticker symbol
            question: Research question
            fundamental_data: Fundamental analysis results
            valuation_data: Valuation analysis results
            technical_data: Technical analysis results
            historical_data: Historical analysis results

        Returns:
            InvestmentReport with structured data
        """
        self.report = create_standard_report(
            ticker=ticker,
            question=question,
            fundamental_data=fundamental_data,
            valuation_data=valuation_data,
            technical_data=technical_data,
            historical_data=historical_data,
        )
        return self.report

    def add_facts_from_data(
        self,
        fundamental_data: Dict[str, Any],
        valuation_data: Dict[str, Any],
    ):
        """
        Extract and add factual claims from analysis data.

        Args:
            fundamental_data: Results from fundamental analysis
            valuation_data: Results from valuation analysis
        """
        if not self.report:
            raise ValueError("No report created. Call create_report() first.")

        # Extract facts from fundamental data
        if "profitability" in fundamental_data:
            prof = fundamental_data["profitability"]

            if prof.get("roe", {}).get("value"):
                roe_val = prof["roe"]["value"]
                self.report.add_fact(
                    self.report.profitability,
                    f"ROE is {roe_val:.2%}" if roe_val < 1 else f"ROE is {roe_val:.2f}",
                    evidence="Calculated from net income and total equity",
                    source="fundamental_analysis",
                )

            if prof.get("net_margin", {}).get("value"):
                margin_val = prof["net_margin"]["value"]
                self.report.add_fact(
                    self.report.profitability,
                    f"Net margin is {margin_val:.2%}" if margin_val < 1 else f"Net margin is {margin_val:.2f}",
                    evidence="Calculated from net income and revenue",
                    source="fundamental_analysis",
                )

        # Extract facts from valuation data
        if "valuations" in valuation_data:
            vals = valuation_data["valuations"]

            if vals.get("pe_ratio", {}).get("value"):
                pe_val = vals["pe_ratio"]["value"]
                self.report.add_fact(
                    self.report.valuation,
                    f"P/E ratio is {pe_val:.2f}",
                    evidence="Price divided by earnings per share",
                    source="valuation_analysis",
                )

            if vals.get("pb_ratio", {}).get("value"):
                pb_val = vals["pb_ratio"]["value"]
                self.report.add_fact(
                    self.report.valuation,
                    f"P/B ratio is {pb_val:.2f}",
                    evidence="Price divided by book value per share",
                    source="valuation_analysis",
                )

    def add_interpretations(
        self,
        fundamental_data: Dict[str, Any],
        valuation_data: Dict[str, Any],
    ):
        """
        Add interpretive claims based on data analysis.

        Args:
            fundamental_data: Results from fundamental analysis
            valuation_data: Results from valuation analysis
        """
        if not self.report:
            raise ValueError("No report created. Call create_report() first.")

        # ROE interpretation
        if "profitability" in fundamental_data:
            prof = fundamental_data["profitability"]
            roe = prof.get("roe", {}).get("value")

            if roe:
                if roe > 0.15:
                    self.report.add_interpretation(
                        self.report.profitability,
                        f"ROE of {roe:.2%} indicates strong profitability relative to equity",
                        confidence=0.8,
                    )
                elif roe > 0.10:
                    self.report.add_interpretation(
                        self.report.profitability,
                        f"ROE of {roe:.2%} is moderate",
                        confidence=0.7,
                    )
                else:
                    self.report.add_interpretation(
                        self.report.profitability,
                        f"ROE of {roe:.2%} is below typical quality threshold",
                        confidence=0.7,
                    )

        # Valuation interpretation
        if "valuations" in valuation_data:
            vals = valuation_data["valuations"]
            pe = vals.get("pe_ratio", {}).get("value")

            if pe:
                if pe < 15:
                    self.report.add_interpretation(
                        self.report.valuation,
                        f"P/E of {pe:.2f} suggests the stock may be undervalued",
                        confidence=0.6,
                    )
                elif pe > 25:
                    self.report.add_interpretation(
                        self.report.valuation,
                        f"P/E of {pe:.2f} suggests the stock may be overvalued",
                        confidence=0.6,
                    )

    def add_assumptions(self, assumptions: List[str]):
        """
        Add explicit assumptions to the report.

        Args:
            assumptions: List of assumption text strings
        """
        if not self.report:
            raise ValueError("No report created. Call create_report() first.")

        for assumption in assumptions:
            self.report.add_assumption(
                self.report.conclusion,
                assumption,
                confidence=0.5,
            )

    def add_speculations(self, speculations: List[str]):
        """
        Add speculative claims to the report.

        Args:
            speculations: List of speculation text strings
        """
        if not self.report:
            raise ValueError("No report created. Call create_report() first.")

        for speculation in speculations:
            self.report.add_speculation(
                self.report.conclusion,
                speculation,
                confidence=0.3,
            )

    def calculate_confidence(self) -> float:
        """
        Calculate overall report confidence score.

        Based on:
        - Ratio of facts to total claims
        - Average confidence of individual claims
        - Data completeness
        """
        if not self.report:
            return 0.0

        stats = self.report.get_summary_stats()
        total_claims = sum(stats.values())

        if total_claims == 0:
            return 0.0

        # Weight facts higher than other claim types
        fact_weight = stats["FACT"] * 1.0
        interp_weight = stats["INTERPRETATION"] * 0.7
        assum_weight = stats["ASSUMPTION"] * 0.5
        spec_weight = stats["SPECULATION"] * 0.3

        weighted_score = (fact_weight + interp_weight + assum_weight + spec_weight) / total_claims

        # Bonus for having multiple data sources
        source_bonus = min(len(self.report.data_sources) * 0.05, 0.2)

        return min(weighted_score + source_bonus, 1.0)

    def finalize_report(self) -> InvestmentReport:
        """
        Finalize the report by calculating confidence and verdict.

        Returns:
            Finalized InvestmentReport
        """
        if not self.report:
            raise ValueError("No report created. Call create_report() first.")

        # Calculate confidence
        self.report.confidence_score = self.calculate_confidence()

        # Generate verdict based on confidence and claim distribution
        stats = self.report.get_summary_stats()

        if stats["SPECULATION"] > stats["FACT"] * 2:
            self.report.overall_verdict = "High uncertainty - predominantly speculative"
        elif stats["FACT"] > stats["SPECULATION"] * 2:
            self.report.overall_verdict = "Well-supported by data"
        else:
            self.report.overall_verdict = "Mixed evidence"

        # Set data timestamp
        self.report.data_timestamp = datetime.now().isoformat()

        return self.report


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def generate_report(
    ticker: str,
    question: str,
    fundamental_data: Optional[Dict] = None,
    valuation_data: Optional[Dict] = None,
    technical_data: Optional[Dict] = None,
    historical_data: Optional[Dict] = None,
) -> InvestmentReport:
    """
    Convenience function to generate a complete research report.

    Args:
        ticker: Stock ticker symbol
        question: Research question
        fundamental_data: Fundamental analysis results
        valuation_data: Valuation analysis results
        technical_data: Technical analysis results
        historical_data: Historical analysis results

    Returns:
        Finalized InvestmentReport
    """
    generator = ReportGenerator()
    report = generator.create_report(
        ticker=ticker,
        question=question,
        fundamental_data=fundamental_data,
        valuation_data=valuation_data,
        technical_data=technical_data,
        historical_data=historical_data,
    )

    # Add extracted facts and interpretations
    generator.add_facts_from_data(
        fundamental_data or {},
        valuation_data or {},
    )
    generator.add_interpretations(
        fundamental_data or {},
        valuation_data or {},
    )

    # Finalize
    return generator.finalize_report()
