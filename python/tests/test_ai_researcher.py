"""
Tests for AI Research Analyst (Phase 11).

Tests cover:
- Researcher initialization and configuration
- Stock analysis workflow
- Stock comparison workflow
- Thesis validation workflow
- Report generation and formatting
- Claim tracking
- Error handling
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.report import ClaimTracker, ResearchReport
from ai.researcher import AIResearcher, analyze_stock, compare_stocks, create_researcher
from ai.tools import (
    get_fundamental_analysis,
    get_stock_price,
    get_technical_analysis,
    get_valuation,
)
from models import FinancialMetrics

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """
# Executive Summary
This is a mock analysis response.

## Business Quality
Good quality company.

## Valuation
Fairly valued.

## Conclusion
Hold position.
"""
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def sample_metrics():
    """Create sample financial metrics for testing."""
    return FinancialMetrics(
        revenue=10000.0,
        net_income=1500.0,
        total_equity=5000.0,
        total_assets=20000.0,
        eps=150.0,
    )


# =============================================================================
# TESTS FOR RESEARCHER INITIALIZATION
# =============================================================================

class TestResearcherInit:
    """Tests for AIResearcher initialization."""

    def test_create_researcher_without_api_key(self, monkeypatch):
        """Test creating researcher without API key (uses mock)."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_MODEL", raising=False)  # Clear model env var
        researcher = AIResearcher(api_key=None)
        assert researcher.model == "gpt-4o"
        assert researcher.client is None

    def test_create_researcher_with_api_key(self, mock_openai_client):
        """Test creating researcher with API key."""
        with patch('ai.researcher.OpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client
            researcher = AIResearcher(api_key="test-key")
            assert researcher.client is not None

    def test_create_researcher_custom_model(self):
        """Test creating researcher with custom model."""
        researcher = AIResearcher(model="gpt-4-turbo")
        assert researcher.model == "gpt-4-turbo"

    def test_create_researcher_with_base_url(self):
        """Test creating researcher with custom base URL."""
        with patch('ai.researcher.OpenAI') as mock_openai:
            mock_openai.return_value = MagicMock()
            researcher = AIResearcher(
                api_key="test",
                base_url="https://custom.api.com"
            )
            mock_openai.assert_called_once_with(
                api_key="test",
                base_url="https://custom.api.com",
                timeout=30.0
            )


# =============================================================================
# TESTS FOR REPORT GENERATION
# =============================================================================

class TestResearchReport:
    """Tests for ResearchReport class."""

    def test_create_report(self):
        """Test creating a basic report."""
        report = ResearchReport(
            ticker="BBCA",
            question="Is BBCA a good investment?",
            executive_summary="BBCA is a strong bank.",
            conclusion="Buy recommendation.",
        )

        assert report.ticker == "BBCA"
        assert report.question == "Is BBCA a good investment?"
        assert "BBCA" in report.executive_summary
        assert "Buy" in report.conclusion

    def test_report_to_dict(self):
        """Test converting report to dictionary."""
        report = ResearchReport(
            ticker="BBCA",
            question="Test question",
            executive_summary="Summary text",
        )

        d = report.to_dict()
        assert d["ticker"] == "BBCA"
        assert d["question"] == "Test question"
        assert "timestamp" in d
        assert "data_sources" in d

    def test_report_to_markdown(self):
        """Test converting report to markdown."""
        report = ResearchReport(
            ticker="BBCA",
            question="Test",
            executive_summary="Summary",
            conclusion="Conclusion",
        )

        md = report.to_markdown()
        assert "# Investment Research Report: BBCA" in md
        assert "**Question:** Test" in md
        assert "## Executive Summary" in md
        assert "## Conclusion" in md

    def test_report_timestamp_default(self):
        """Test that timestamp defaults to now."""
        before = datetime.now()
        report = ResearchReport(ticker="BBCA", question="Test")
        after = datetime.now()

        assert before <= report.timestamp <= after

    def test_report_confidence_default(self):
        """Test that confidence defaults to 0."""
        report = ResearchReport(ticker="BBCA", question="Test")
        assert report.confidence == 0.0


# =============================================================================
# TESTS FOR CLAIM TRACKER
# =============================================================================

class TestClaimTracker:
    """Tests for ClaimTracker class."""

    def test_add_claim(self):
        """Test adding a claim."""
        tracker = ClaimTracker()
        tracker.add_claim(
            claim="ROE is 25%",
            type_="FACT",
            evidence="Fundamental analysis shows ROE of 0.25",
            source="fundamental_analysis",
        )

        assert len(tracker.claims) == 1
        assert tracker.claims[0]["claim"] == "ROE is 25%"
        assert tracker.claims[0]["type"] == "FACT"

    def test_get_claims_by_type(self):
        """Test filtering claims by type."""
        tracker = ClaimTracker()
        tracker.add_claim("Fact 1", "FACT")
        tracker.add_claim("Interpretation 1", "INTERPRETATION")
        tracker.add_claim("Fact 2", "FACT")

        facts = tracker.get_claims_by_type("FACT")
        assert len(facts) == 2
        assert all(c["type"] == "FACT" for c in facts)

    def test_get_summary(self):
        """Test getting claim summary."""
        tracker = ClaimTracker()
        tracker.add_claim("Fact 1", "FACT")
        tracker.add_claim("Fact 2", "FACT")
        tracker.add_claim("Speculation 1", "SPECULATION")
        tracker.add_claim("Assumption 1", "ASSUMPTION")

        summary = tracker.get_summary()
        assert summary["FACT"] == 2
        assert summary["SPECULATION"] == 1
        assert summary["ASSUMPTION"] == 1
        assert summary["total_claims"] == 4

    def test_tracker_to_dict(self):
        """Test converting tracker to dictionary."""
        tracker = ClaimTracker()
        tracker.add_claim("Test claim", "FACT")

        d = tracker.to_dict()
        assert "claims" in d
        assert "summary" in d
        assert "total_claims" in d


# =============================================================================
# TESTS FOR RESEARCH WORKFLOW
# =============================================================================

class TestResearchWorkflow:
    """Tests for research workflow functions."""

    def test_analyze_stock_returns_report(self, monkeypatch):
        """Test analyzing a stock returns a report."""
        # Mock the LLM call to avoid network dependency
        def mock_call_llm(self, messages):
            return "# Test Response\n\nThis is a test analysis."

        monkeypatch.setattr(AIResearcher, '_call_llm', mock_call_llm)

        report = analyze_stock("BBCA", question="Test question")

        assert isinstance(report, ResearchReport)
        assert report.ticker == "BBCA"
        assert report.question == "Test question"

    def test_analyze_stock_with_api_key(self, mock_openai_client):
        """Test analyzing stock with mocked API."""
        with patch('ai.researcher.OpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client
            report = analyze_stock("BBCA", api_key="test-key")

            assert isinstance(report, ResearchReport)
            assert report.data_sources is not None

    def test_compare_stocks_returns_report(self, monkeypatch):
        """Test comparing stocks returns a report."""
        # Mock the LLM call
        def mock_call_llm(self, messages):
            return "# Comparison\n\nThese stocks are similar."

        monkeypatch.setattr(AIResearcher, '_call_llm', mock_call_llm)

        report = compare_stocks(["BBCA", "BBRI"], question="Compare these")

        assert isinstance(report, ResearchReport)
        assert report.ticker == "BBCA"  # Uses first ticker

    def test_create_researcher_convenience(self):
        """Test convenience function for creating researcher."""
        researcher = create_researcher()
        assert isinstance(researcher, AIResearcher)

    def test_researcher_analyze_method(self, monkeypatch):
        """Test researcher.analyze_stock method."""
        # Mock the LLM call
        def mock_call_llm(self, messages):
            return "# Analysis\n\nTest analysis result."

        monkeypatch.setattr(AIResearcher, '_call_llm', mock_call_llm)

        researcher = AIResearcher()
        report = researcher.analyze_stock("BBCA")

        assert isinstance(report, ResearchReport)
        assert report.ticker == "BBCA"


# =============================================================================
# TESTS FOR DATA CONTEXT PREPARATION
# =============================================================================

class TestDataContext:
    """Tests for data context preparation."""

    def test_prepare_data_context(self):
        """Test preparing data context for LLM."""
        researcher = AIResearcher()

        fundamental_data = get_fundamental_analysis("BBCA")
        valuation_data = get_valuation("BBCA")
        technical_data = get_technical_analysis("BBCA")

        context = researcher._prepare_data_context(
            ticker="BBCA",
            fundamental_data=fundamental_data,
            valuation_data=valuation_data,
            technical_data=technical_data,
            historical_data={},
        )

        assert "BBCA" in context
        assert "Fundamental Analysis" in context
        assert "Valuation Analysis" in context

    def test_prepare_empty_context(self):
        """Test preparing empty data context."""
        researcher = AIResearcher()

        context = researcher._prepare_data_context(
            ticker="BBCA",
            fundamental_data={},
            valuation_data={},
            technical_data={},
            historical_data={},
        )

        assert "BBCA" in context


# =============================================================================
# TESTS FOR ERROR HANDLING
# =============================================================================

class TestErrorHandling:
    """Tests for error handling."""

    def test_mock_response_on_missing_api(self):
        """Test that mock response is returned when API key is missing."""
        researcher = AIResearcher(api_key=None)

        response = researcher._mock_llm_response([
            {"role": "user", "content": "Test"}
        ])

        assert "[MOCK RESPONSE" in response

    def test_parse_report_response_basic(self):
        """Test parsing report response with basic structure."""
        researcher = AIResearcher()

        response = """
# Executive Summary
This is the summary.

## Conclusion
This is the conclusion.
"""

        report = researcher._parse_report_response("BBCA", "Test", response)

        assert "summary" in report.executive_summary.lower()
        assert "conclusion" in report.conclusion.lower()

    def test_parse_report_response_no_sections(self):
        """Test parsing response with no section headers."""
        researcher = AIResearcher()

        response = "This is a plain text response with no headers."

        report = researcher._parse_report_response("BBCA", "Test", response)

        # Should fall back to putting everything in executive summary
        assert "plain text" in report.executive_summary.lower()


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for the research pipeline."""

    def test_full_analysis_pipeline(self, monkeypatch):
        """Test full analysis pipeline from question to report."""
        # Mock the LLM call to avoid network dependency
        def mock_call_llm(self, messages):
            return "# Test Response\n\nThis is a test analysis of BBCA."

        monkeypatch.setattr(AIResearcher, '_call_llm', mock_call_llm)

        # Step 1: Get raw data
        price_data = get_stock_price("BBCA")
        fundamental_data = get_fundamental_analysis("BBCA")

        # Step 2: Verify data structures
        assert isinstance(price_data, dict)
        assert isinstance(fundamental_data, dict)
        assert price_data["ticker"] == "BBCA"

        # Step 3: Generate report
        report = analyze_stock("BBCA", question="What is BBCA worth?")

        # Step 4: Verify report
        assert isinstance(report, ResearchReport)
        assert report.ticker == "BBCA"
        assert report.question == "What is BBCA worth?"

    def test_claim_tracking_in_analysis(self):
        """Test that claims can be tracked during analysis."""
        tracker = ClaimTracker()

        # Simulate adding claims during analysis
        tracker.add_claim(
            "ROE > 15%",
            "FACT",
            evidence="Fundamental analysis shows ROE of 25%",
            source="fundamental_analysis",
        )
        tracker.add_claim(
            "Stock is undervalued",
            "SPECULATION",
            confidence=0.6,
        )

        summary = tracker.get_summary()
        assert summary["FACT"] == 1
        assert summary["SPECULATION"] == 1
        assert summary["total_claims"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
