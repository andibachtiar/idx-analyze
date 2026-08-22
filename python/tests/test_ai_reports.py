"""
Tests for AI Research Report (Phase 12).

Tests cover:
- Report structure and formatting
- Claim type tracking
- Confidence scoring
- Fact vs speculation separation
- Markdown and JSON output
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.enhanced_report import ReportGenerator, generate_report
from ai.report_templates import (
    Claim,
    ClaimType,
    InvestmentReport,
    ReportSection,
    create_standard_report,
)

# =============================================================================
# TESTS FOR CLAIM CLASS
# =============================================================================

class TestClaim:
    """Tests for Claim dataclass."""

    def test_create_fact_claim(self):
        """Test creating a FACT claim."""
        claim = Claim(
            text="ROE is 25%",
            claim_type=ClaimType.FACT,
            evidence="Calculated from financial statements",
            source="fundamental_analysis",
        )

        assert claim.text == "ROE is 25%"
        assert claim.claim_type == ClaimType.FACT
        assert claim.confidence == 1.0

    def test_create_speculation_claim(self):
        """Test creating a SPECULATION claim."""
        claim = Claim(
            text="Stock may rise 20% next year",
            claim_type=ClaimType.SPECULATION,
            confidence=0.3,
        )

        assert claim.claim_type == ClaimType.SPECULATION
        assert claim.confidence == 0.3

    def test_claim_to_dict(self):
        """Test converting claim to dictionary."""
        claim = Claim(
            text="Test claim",
            claim_type=ClaimType.FACT,
            evidence="Evidence here",
            source="test_source",
        )

        d = claim.to_dict()
        assert d["text"] == "Test claim"
        assert d["type"] == "FACT"
        assert d["evidence"] == "Evidence here"
        assert d["source"] == "test_source"
        assert d["confidence"] == 1.0


# =============================================================================
# TESTS FOR REPORT SECTION
# =============================================================================

class TestReportSection:
    """Tests for ReportSection class."""

    def test_create_section(self):
        """Test creating a report section."""
        section = ReportSection(title="Test Section")
        assert section.title == "Test Section"
        assert section.content == ""
        assert section.claims == []

    def test_add_claim(self):
        """Test adding a claim to a section."""
        section = ReportSection(title="Test")
        claim = Claim(text="Test claim", claim_type=ClaimType.FACT)

        section.add_claim(claim)
        assert len(section.claims) == 1
        assert section.claims[0].text == "Test claim"

    def test_add_subsection(self):
        """Test adding a subsection."""
        section = ReportSection(title="Parent")
        sub = ReportSection(title="Child")

        section.add_subsection("Child Section", sub)
        assert "Child Section" in section.sub_sections

    def test_section_to_dict(self):
        """Test converting section to dictionary."""
        section = ReportSection(title="Test")
        section.content = "Some content"
        section.add_claim(Claim(text="Claim 1", claim_type=ClaimType.FACT))

        d = section.to_dict()
        assert d["title"] == "Test"
        assert d["content"] == "Some content"
        assert len(d["claims"]) == 1


# =============================================================================
# TESTS FOR INVESTMENT REPORT
# =============================================================================

class TestInvestmentReport:
    """Tests for InvestmentReport class."""

    def test_create_report(self):
        """Test creating a basic report."""
        report = InvestmentReport(
            ticker="BBCA",
            question="Is BBCA a good investment?",
        )

        assert report.ticker == "BBCA"
        assert "BBCA" in report.question
        assert report.generated_at is not None

    def test_add_fact(self):
        """Test adding a fact to a section."""
        report = InvestmentReport(ticker="BBCA", question="Test")
        report.add_fact(report.profitability, "ROE is 25%", source="test")

        claims = report.get_claims_by_type(ClaimType.FACT)
        assert len(claims) == 1
        assert claims[0].text == "ROE is 25%"

    def test_add_interpretation(self):
        """Test adding an interpretation."""
        report = InvestmentReport(ticker="BBCA", question="Test")
        report.add_interpretation(report.profitability, "Strong ROE", confidence=0.8)

        claims = report.get_claims_by_type(ClaimType.INTERPRETATION)
        assert len(claims) == 1
        assert claims[0].confidence == 0.8

    def test_add_assumption(self):
        """Test adding an assumption."""
        report = InvestmentReport(ticker="BBCA", question="Test")
        report.add_assumption(report.conclusion, "Market will remain stable", confidence=0.6)

        claims = report.get_claims_by_type(ClaimType.ASSUMPTION)
        assert len(claims) == 1

    def test_add_speculation(self):
        """Test adding a speculation."""
        report = InvestmentReport(ticker="BBCA", question="Test")
        report.add_speculation(report.conclusion, "Stock could double", confidence=0.3)

        claims = report.get_claims_by_type(ClaimType.SPECULATION)
        assert len(claims) == 1

    def test_get_claims_by_type(self):
        """Test filtering claims by type."""
        report = InvestmentReport(ticker="BBCA", question="Test")

        report.add_fact(report.profitability, "Fact 1")
        report.add_fact(report.profitability, "Fact 2")
        report.add_interpretation(report.valuation, "Interpretation 1")
        report.add_speculation(report.conclusion, "Speculation 1")

        facts = report.get_claims_by_type(ClaimType.FACT)
        interpretations = report.get_claims_by_type(ClaimType.INTERPRETATION)
        speculations = report.get_claims_by_type(ClaimType.SPECULATION)

        assert len(facts) == 2
        assert len(interpretations) == 1
        assert len(speculations) == 1

    def test_get_summary_stats(self):
        """Test getting claim summary statistics."""
        report = InvestmentReport(ticker="BBCA", question="Test")

        report.add_fact(report.profitability, "Fact 1")
        report.add_fact(report.profitability, "Fact 2")
        report.add_interpretation(report.valuation, "Interp 1")
        report.add_assumption(report.conclusion, "Assump 1")
        report.add_speculation(report.conclusion, "Spec 1")

        stats = report.get_summary_stats()

        assert stats["FACT"] == 2
        assert stats["INTERPRETATION"] == 1
        assert stats["ASSUMPTION"] == 1
        assert stats["SPECULATION"] == 1

    def test_report_to_dict(self):
        """Test converting report to dictionary."""
        report = InvestmentReport(ticker="BBCA", question="Test")
        report.add_fact(report.profitability, "ROE is 25%")

        d = report.to_dict()

        assert d["ticker"] == "BBCA"
        assert "generated_at" in d
        assert "claim_summary" in d
        assert "sections" in d

    def test_report_to_markdown(self):
        """Test converting report to markdown."""
        report = InvestmentReport(
            ticker="BBCA",
            question="Test question",
            confidence_score=0.75,
        )
        report.add_fact(report.profitability, "ROE is 25%")
        report.add_speculation(report.conclusion, "Stock may rise")

        md = report.to_markdown()

        assert "# Investment Research Report: BBCA" in md
        assert "**Question:** Test question" in md
        assert "**Confidence Score:** 75.0%" in md
        assert "## Profitability" in md
        assert "## Conclusion" in md

    def test_report_repr(self):
        """Test report string representation."""
        report = InvestmentReport(ticker="BBCA", question="Test", confidence_score=0.8)

        assert "BBCA" in repr(report)
        assert "80.0%" in repr(report)


# =============================================================================
# TESTS FOR REPORT GENERATOR
# =============================================================================

class TestReportGenerator:
    """Tests for ReportGenerator class."""

    def test_create_report(self):
        """Test creating a report via generator."""
        generator = ReportGenerator()
        report = generator.create_report(
            ticker="BBCA",
            question="Test question",
        )

        assert isinstance(report, InvestmentReport)
        assert report.ticker == "BBCA"

    def test_add_facts_from_data(self):
        """Test extracting facts from analysis data."""
        generator = ReportGenerator()
        generator.create_report(ticker="BBCA", question="Test")

        fundamental_data = {
            "profitability": {
                "roe": {"value": 0.25},
                "net_margin": {"value": 0.15},
            }
        }
        valuation_data = {
            "valuations": {
                "pe_ratio": {"value": 15.0},
            }
        }

        generator.add_facts_from_data(fundamental_data, valuation_data)

        facts = generator.report.get_claims_by_type(ClaimType.FACT)
        assert len(facts) >= 2

    def test_add_interpretations(self):
        """Test adding interpretations from data."""
        generator = ReportGenerator()
        generator.create_report(ticker="BBCA", question="Test")

        fundamental_data = {
            "profitability": {
                "roe": {"value": 0.20},
            }
        }

        generator.add_interpretations(fundamental_data, {})

        interpretations = generator.report.get_claims_by_type(ClaimType.INTERPRETATION)
        assert len(interpretations) >= 1

    def test_add_assumptions(self):
        """Test adding assumptions."""
        generator = ReportGenerator()
        generator.create_report(ticker="BBCA", question="Test")

        generator.add_assumptions([
            "Market conditions will remain stable",
            "No major regulatory changes expected",
        ])

        assumptions = generator.report.get_claims_by_type(ClaimType.ASSUMPTION)
        assert len(assumptions) == 2

    def test_add_speculations(self):
        """Test adding speculations."""
        generator = ReportGenerator()
        generator.create_report(ticker="BBCA", question="Test")

        generator.add_speculations([
            "Stock price could reach 10000",
            "Company may expand internationally",
        ])

        speculations = generator.report.get_claims_by_type(ClaimType.SPECULATION)
        assert len(speculations) == 2

    def test_calculate_confidence(self):
        """Test confidence calculation."""
        generator = ReportGenerator()
        generator.create_report(ticker="BBCA", question="Test")

        # Add mixed claims
        generator.add_facts_from_data(
            {"profitability": {"roe": {"value": 0.25}}},
            {"valuations": {"pe_ratio": {"value": 15.0}}},
        )
        generator.add_interpretations(
            {"profitability": {"roe": {"value": 0.25}}},
            {},
        )

        confidence = generator.calculate_confidence()

        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.0  # Should have some confidence with facts

    def test_finalize_report(self):
        """Test finalizing a report."""
        generator = ReportGenerator()
        generator.create_report(ticker="BBCA", question="Test")
        generator.add_facts_from_data(
            {"profitability": {"roe": {"value": 0.25}}},
            {"valuations": {"pe_ratio": {"value": 15.0}}},
        )

        report = generator.finalize_report()

        assert report.confidence_score > 0
        assert report.overall_verdict != ""
        assert report.data_timestamp is not None


# =============================================================================
# TESTS FOR CONVENIENCE FUNCTIONS
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_generate_report(self):
        """Test generate_report convenience function."""
        report = generate_report(
            ticker="BBCA",
            question="Is BBCA a good investment?",
            fundamental_data={
                "profitability": {"roe": {"value": 0.25}},
            },
            valuation_data={
                "valuations": {"pe_ratio": {"value": 15.0}},
            },
        )

        assert isinstance(report, InvestmentReport)
        assert report.ticker == "BBCA"
        assert report.confidence_score > 0

    def test_create_standard_report(self):
        """Test create_standard_report factory function."""
        report = create_standard_report(
            ticker="BBCA",
            question="Test",
            fundamental_data={"profitability": {"roe": {"value": 0.20}}},
        )

        assert report.ticker == "BBCA"
        assert "fundamental_analysis" in report.data_sources


# =============================================================================
# TESTS FOR DATA FORMATTING
# =============================================================================

class TestDataFormatting:
    """Tests for data formatting functions."""

    def test_format_fundamental_content(self):
        """Test formatting fundamental data."""
        from ai.report_templates import _format_fundamental_content

        data = {
            "profitability": {
                "roe": {"value": 0.25},
                "net_margin": {"value": 0.15},
            }
        }

        content = _format_fundamental_content(data)

        assert "ROE" in content
        assert "25.00%" in content
        assert "Net Margin" in content

    def test_format_valuation_content(self):
        """Test formatting valuation data."""
        from ai.report_templates import _format_valuation_content

        data = {
            "valuations": {
                "pe_ratio": {"value": 15.0},
                "pb_ratio": {"value": 2.5},
            },
            "historical_comparison": {
                "pe_ratio": {"percentile": 45.0},
            }
        }

        content = _format_valuation_content(data)

        assert "P/E Ratio" in content
        assert "15.00" in content
        assert "P/B Ratio" in content

    def test_format_technical_content(self):
        """Test formatting technical data."""
        from ai.report_templates import _format_technical_content

        data = {
            "indicators": {
                "sma_20": {"value": 8500.0},
                "sma_50": {"value": 8200.0},
                "sma_200": {"value": 7800.0},
                "rsi_14": {"value": 65.0},
            },
            "signals": {
                "trend": "bullish",
                "rsi": "neutral",
            }
        }

        content = _format_technical_content(data)

        assert "SMA 20" in content
        assert "RSI" in content
        assert "bullish" in content

    def test_format_historical_content(self):
        """Test formatting historical data."""
        from ai.report_templates import _format_historical_content

        data = {
            "growth": {
                "revenue": {"value": 0.12},
                "earnings": {"value": 0.15},
            },
            "trends": {
                "revenue": "up",
                "earnings": "up",
            }
        }

        content = _format_historical_content(data)

        assert "Growth Rates" in content
        assert "12.00%" in content
        assert "Trends" in content


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for report generation."""

    def test_full_report_generation(self):
        """Test generating a complete report."""
        report = generate_report(
            ticker="BBCA",
            question="Should I invest in BBCA?",
            fundamental_data={
                "profitability": {
                    "roe": {"value": 0.25},
                    "net_margin": {"value": 0.18},
                },
                "financial_health": {
                    "debt_to_equity": {"value": 0.3},
                }
            },
            valuation_data={
                "valuations": {
                    "pe_ratio": {"value": 15.0},
                    "pb_ratio": {"value": 3.5},
                },
                "historical_comparison": {
                    "pe_ratio": {"percentile": 40.0},
                }
            },
            technical_data={
                "indicators": {
                    "sma_200": {"value": 8000.0},
                    "rsi_14": {"value": 55.0},
                },
                "signals": {
                    "trend": "bullish",
                }
            },
            historical_data={
                "growth": {
                    "revenue": {"value": 0.10},
                    "earnings": {"value": 0.12},
                }
            },
        )

        # Verify structure
        assert report.ticker == "BBCA"
        assert report.confidence_score > 0
        assert len(report.data_sources) > 0

        # Verify claims
        facts = report.get_claims_by_type(ClaimType.FACT)
        assert len(facts) > 0

        # Verify output formats
        md = report.to_markdown()
        assert "# Investment Research Report: BBCA" in md

        d = report.to_dict()
        assert d["ticker"] == "BBCA"
        assert "sections" in d

    def test_report_with_only_specs(self):
        """Test report where speculation exceeds facts."""
        generator = ReportGenerator()
        generator.create_report(ticker="BBCA", question="Test")

        generator.add_speculations([
            "Stock will double",
            "Company will acquire competitors",
        ])
        generator.add_speculations([
            "Market will crash",
        ])

        report = generator.finalize_report()

        # Should have high speculation ratio
        stats = report.get_summary_stats()
        assert stats["SPECULATION"] > stats["FACT"]
        assert "uncertainty" in report.overall_verdict.lower()

    def test_report_with_only_facts(self):
        """Test report with mostly facts."""
        generator = ReportGenerator()
        generator.create_report(ticker="BBCA", question="Test")

        generator.add_facts_from_data(
            {"profitability": {"roe": {"value": 0.25}}},
            {"valuations": {"pe_ratio": {"value": 15.0}}},
        )
        generator.add_interpretations(
            {"profitability": {"roe": {"value": 0.25}}},
            {"valuations": {"pe_ratio": {"value": 15.0}}},
        )

        report = generator.finalize_report()

        # Should have good fact ratio
        stats = report.get_summary_stats()
        assert stats["FACT"] >= stats["SPECULATION"]
        assert "supported" in report.overall_verdict.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
