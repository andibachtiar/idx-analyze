"""
Tests for Research Memory (Phase 13).

Tests cover:
- Report saving and retrieval
- Thesis comparison
- Claim tracking over time
- Statistics and housekeeping
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime
from typing import Dict, List

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.memory import (
    ResearchMemory,
    compare_research_theses,
    get_research_history,
    save_research_report,
)
from ai.report_templates import ClaimType, InvestmentReport, ReportSection

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_storage():
    """Create a temporary storage directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_report():
    """Create a sample research report for testing."""
    return InvestmentReport(
        ticker="BBCA",
        question="Is BBCA a good investment?",
        executive_summary=ReportSection(title="Executive Summary", content="BBCA is a strong bank with good fundamentals."),
        confidence_score=0.75,
        overall_verdict="Buy",
    )


@pytest.fixture
def sample_report_dict(sample_report):
    """Create a sample report as dictionary."""
    return sample_report.to_dict()


# =============================================================================
# TESTS FOR RESEARCH MEMORY
# =============================================================================

class TestResearchMemory:
    """Tests for ResearchMemory class."""

    def test_init_creates_directory(self, temp_storage):
        """Test that initialization creates storage directory."""
        memory = ResearchMemory(storage_path=temp_storage)
        assert os.path.exists(temp_storage)

    def test_save_report(self, temp_storage, sample_report_dict):
        """Test saving a report."""
        memory = ResearchMemory(storage_path=temp_storage)
        filepath = memory.save_report("BBCA", sample_report_dict, question="Test question")

        assert os.path.exists(filepath)
        assert "BBCA" in filepath
        assert filepath.endswith(".json")

    def test_save_report_with_metadata(self, temp_storage, sample_report_dict):
        """Test saving report with metadata."""
        memory = ResearchMemory(storage_path=temp_storage)
        metadata = {"price": 8500, "market_cap": "500T"}
        filepath = memory.save_report("BBCA", sample_report_dict, metadata=metadata)

        # Verify metadata was saved
        with open(filepath, 'r') as f:
            data = json.load(f)
        assert "metadata" in data
        assert data["metadata"]["price"] == 8500

    def test_get_reports_for_ticker(self, temp_storage, sample_report_dict):
        """Test retrieving reports for a ticker."""
        memory = ResearchMemory(storage_path=temp_storage)

        # Save multiple reports
        memory.save_report("BBCA", sample_report_dict, question="Q1")
        memory.save_report("BBCA", sample_report_dict, question="Q2")
        memory.save_report("BBRI", sample_report_dict, question="Q1")

        # Get BBCA reports
        reports = memory.get_reports_for_ticker("BBCA")
        assert len(reports) == 2

        # Get BBRI reports
        reports = memory.get_reports_for_ticker("BBRI")
        assert len(reports) == 1

    def test_get_latest_report(self, temp_storage, sample_report_dict):
        """Test getting the latest report."""
        memory = ResearchMemory(storage_path=temp_storage)

        # Save reports
        memory.save_report("BBCA", sample_report_dict, question="First")
        memory.save_report("BBCA", sample_report_dict, question="Second")

        latest = memory.get_latest_report("BBCA")
        assert latest is not None
        assert latest["question"] == "Second"

    def test_get_latest_report_not_found(self, temp_storage):
        """Test getting latest report when none exists."""
        memory = ResearchMemory(storage_path=temp_storage)
        latest = memory.get_latest_report("NONEXIST")
        assert latest is None

    def test_compare_theses(self, temp_storage, sample_report_dict):
        """Test comparing multiple theses."""
        memory = ResearchMemory(storage_path=temp_storage)

        # Save reports with different confidence
        report1 = sample_report_dict.copy()
        report1["confidence_score"] = 0.6
        report1["overall_verdict"] = "Hold"
        memory.save_report("BBCA", report1, question="First analysis")

        report2 = sample_report_dict.copy()
        report2["confidence_score"] = 0.8
        report2["overall_verdict"] = "Buy"
        memory.save_report("BBCA", report2, question="Second analysis")

        comparison = memory.compare_theses("BBCA")

        assert comparison["ticker"] == "BBCA"
        assert comparison["reports_analyzed"] == 2
        assert len(comparison["comparisons"]) == 1

        comp = comparison["comparisons"][0]
        assert comp["confidence_change"]["direction"] == "increased"
        assert comp["verdict_change"]["changed"] is True

    def test_compare_theses_insufficient_data(self, temp_storage, sample_report_dict):
        """Test comparison with insufficient reports."""
        memory = ResearchMemory(storage_path=temp_storage)
        memory.save_report("BBCA", sample_report_dict)

        comparison = memory.compare_theses("BBCA")
        assert "Insufficient reports" in comparison["notes"]

    def test_delete_report(self, temp_storage, sample_report_dict):
        """Test deleting a report."""
        memory = ResearchMemory(storage_path=temp_storage)
        filepath = memory.save_report("BBCA", sample_report_dict)

        # Delete by filename
        filename = os.path.basename(filepath)
        result = memory.delete_report("BBCA", filename)
        assert result is True

        # Verify deleted
        reports = memory.get_reports_for_ticker("BBCA")
        assert len(reports) == 0

    def test_delete_all_reports(self, temp_storage, sample_report_dict):
        """Test deleting all reports for a ticker."""
        memory = ResearchMemory(storage_path=temp_storage)

        memory.save_report("BBCA", sample_report_dict)
        memory.save_report("BBCA", sample_report_dict)

        result = memory.delete_report("BBCA")
        assert result is True

        reports = memory.get_reports_for_ticker("BBCA")
        assert len(reports) == 0

    def test_get_statistics(self, temp_storage, sample_report_dict):
        """Test getting storage statistics."""
        memory = ResearchMemory(storage_path=temp_storage)

        # Save some reports
        memory.save_report("BBCA", sample_report_dict)
        memory.save_report("BBCA", sample_report_dict)
        memory.save_report("BBRI", sample_report_dict)

        stats = memory.get_statistics()

        assert stats["total_reports"] == 3
        assert stats["unique_tickers"] == 2
        assert stats["tickers"]["BBCA"] == 2
        assert stats["tickers"]["BBRI"] == 1

    def test_get_statistics_empty(self, temp_storage):
        """Test statistics with no reports."""
        memory = ResearchMemory(storage_path=temp_storage)
        stats = memory.get_statistics()

        assert stats["total_reports"] == 0
        assert stats["unique_tickers"] == 0


# =============================================================================
# TESTS FOR CONVENIENCE FUNCTIONS
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_save_research_report(self, temp_storage, sample_report_dict):
        """Test save_research_report convenience function."""
        filepath = save_research_report(
            "BBCA",
            sample_report_dict,
            question="Test",
            storage_path=temp_storage
        )
        assert os.path.exists(filepath)

    def test_get_research_history(self, temp_storage, sample_report_dict):
        """Test get_research_history convenience function."""
        save_research_report("BBCA", sample_report_dict, storage_path=temp_storage)
        save_research_report("BBCA", sample_report_dict, storage_path=temp_storage)

        history = get_research_history("BBCA", storage_path=temp_storage)
        assert len(history) == 2

    def test_compare_research_theses(self, temp_storage, sample_report_dict):
        """Test compare_research_theses convenience function."""
        report1 = sample_report_dict.copy()
        report1["confidence_score"] = 0.5
        save_research_report("BBCA", report1, storage_path=temp_storage)

        report2 = sample_report_dict.copy()
        report2["confidence_score"] = 0.8
        save_research_report("BBCA", report2, storage_path=temp_storage)

        comparison = compare_research_theses("BBCA", storage_path=temp_storage)
        assert comparison["reports_analyzed"] == 2


# =============================================================================
# TESTS FOR CLAIM TRACKING
# =============================================================================

class TestClaimTracking:
    """Tests for claim tracking over time."""

    def test_claim_summary_in_report(self, sample_report):
        """Test that report has claim summary."""
        d = sample_report.to_dict()
        assert "claim_summary" in d

    def test_claim_summary_counts(self, sample_report):
        """Test claim summary has correct counts."""
        # Add some claims
        sample_report.add_fact(sample_report.profitability, "ROE is 25%")
        sample_report.add_speculation(sample_report.conclusion, "Stock may rise")

        d = sample_report.to_dict()
        summary = d["claim_summary"]

        assert summary["FACT"] == 1
        assert summary["SPECULATION"] == 1
        assert summary["total_claims"] == 2

    def test_thesis_evolution_tracking(self, temp_storage, sample_report):
        """Test tracking how thesis evolves over time."""
        memory = ResearchMemory(storage_path=temp_storage)

        # First analysis - bullish
        report1 = InvestmentReport(
            ticker="BBCA",
            question="Should I buy BBCA?",
            confidence_score=0.8,
            overall_verdict="Strong Buy",
        )
        report1.add_fact(report1.profitability, "ROE is 25%", source="fundamental_analysis")
        memory.save_report("BBCA", report1, question="Initial analysis")

        # Second analysis - more cautious
        report2 = InvestmentReport(
            ticker="BBCA",
            question="Should I buy BBCA?",
            confidence_score=0.6,
            overall_verdict="Hold",
        )
        report2.add_fact(report2.profitability, "ROE is 22%", source="fundamental_analysis")
        report2.add_speculation(report2.conclusion, "Market may correct")
        memory.save_report("BBCA", report2, question="Follow-up analysis")

        # Compare
        comparison = memory.compare_theses("BBCA")
        comp = comparison["comparisons"][0]

        # Confidence should have decreased
        assert comp["confidence_change"]["direction"] == "decreased"
        # Verdict should have changed
        assert comp["verdict_change"]["changed"] is True


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for research memory."""

    def test_full_workflow(self, temp_storage):
        """Test complete save-retrieve-compare workflow."""
        # Create memory
        memory = ResearchMemory(storage_path=temp_storage)

        # Create and save initial report
        report1 = InvestmentReport(
            ticker="BBCA",
            question="Is BBCA undervalued?",
            confidence_score=0.7,
            overall_verdict="Buy",
        )
        report1.add_fact(report1.valuation, "P/E is 15", source="valuation_analysis")
        report1.add_interpretation(report1.valuation, "Below historical average", confidence=0.7)

        filepath1 = memory.save_report("BBCA", report1, question="Initial analysis")

        # Create and save follow-up report
        report2 = InvestmentReport(
            ticker="BBCA",
            question="Is BBCA undervalued?",
            confidence_score=0.6,
            overall_verdict="Hold",
        )
        report2.add_fact(report2.valuation, "P/E is 18", source="valuation_analysis")
        report2.add_speculation(report2.conclusion, "May re-rate higher")

        filepath2 = memory.save_report("BBCA", report2, question="Follow-up")

        # Retrieve and compare
        reports = memory.get_reports_for_ticker("BBCA")
        assert len(reports) == 2

        comparison = memory.compare_theses("BBCA")
        assert comparison["reports_analyzed"] == 2
        assert len(comparison["comparisons"]) == 1

        # Verify statistics
        stats = memory.get_statistics()
        assert stats["total_reports"] == 2
        assert stats["unique_tickers"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
