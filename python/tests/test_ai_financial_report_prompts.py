"""Tests for Financial Report Analyst Prompt Integration (Phase 19)."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.prompts.financial_report import (
    DocumentInfo,
    FinancialHealth,
    FinancialReportAnalysis,
    ManagementCredibility,
    RiskAssessment,
    analyze_financial_report,
    generate_financial_report_prompt,
)


@pytest.fixture
def sample_analysis():
    return FinancialReportAnalysis(
        ticker="AAPL",
        document_info=DocumentInfo(
            filing_type="10-K",
            period_covered="2024-09-30",
            auditor_name="XYZ Auditors",
            auditor_opinion="unqualified",
            filing_date="2024-11-01",
        ),
        financial_health=FinancialHealth(
            revenue_growth_yoy=0.08,
            gross_margin=0.45,
            operating_margin=0.30,
            fcf_margin=0.25,
            net_debt=50000000000,
            debt_to_ebitda=1.5,
        ),
        risk_assessment=RiskAssessment(accounting_quality_score=8.0),
        management_credibility=ManagementCredibility(),
        overall_signal="BULLISH",
        score=8.5,
        action="BUY",
        key_positives=["Strong margin expansion", "Healthy FCF conversion"],
        key_negatives=["Moderate debt levels"],
        analysis_date="2024-11-15",
    )


class TestAnalyzeFinancialReport:
    def test_basic_analysis(self):
        result = analyze_financial_report(
            ticker="TEST",
            filing_type="10-K",
            revenue=1000000000,
            net_income=150000000,
            gross_margin=0.45,
            operating_margin=0.25,
            fcf=120000000,
            total_debt=500000000,
            cash=100000000,
        )
        assert result.ticker == "TEST"
        assert result.action in ["BUY", "HOLD", "SELL"]
        assert 0 <= result.score <= 10

    def test_adverse_auditor_opinion(self):
        result = analyze_financial_report(
            ticker="TEST",
            filing_type="10-K",
            revenue=1000000000,
            net_income=150000000,
            gross_margin=0.45,
            operating_margin=0.25,
            fcf=120000000,
            total_debt=500000000,
            auditor_opinion="adverse",
        )
        assert result.risk_assessment.accounting_quality_score < 7.0

    def test_high_leverage(self):
        result = analyze_financial_report(
            ticker="TEST",
            filing_type="10-K",
            revenue=1000000000,
            net_income=50000000,
            gross_margin=0.30,
            operating_margin=0.10,
            fcf=20000000,
            total_debt=2000000000,
        )
        assert result.financial_health.debt_to_ebitda > 3.0


class TestPromptGeneration:
    def test_generate_prompt(self, sample_analysis):
        prompt = generate_financial_report_prompt("AAPL", sample_analysis)
        assert isinstance(prompt, str)
        assert "AAPL" in prompt
        assert "10-K" in prompt


class TestToDict:
    def test_to_dict(self, sample_analysis):
        d = sample_analysis.to_dict()
        assert d["ticker"] == "AAPL"
        assert d["signal"] == "BULLISH"
        assert "key_positives" in d


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
