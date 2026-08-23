"""Tests for Institutional Ownership Prompt Integration (Phase 22)."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.prompts.institutional_ownership import (
    InstitutionalOwnershipResult,
    analyze_institutional_ownership,
    generate_institutional_ownership_prompt,
)


@pytest.fixture
def sample_result():
    return InstitutionalOwnershipResult(
        ticker="AAPL",
        total_institutional_ownership=71.5,
        num_holders=850,
        top_holders=[],
        ownership_trends=[],
        concentration_top10=40.0,
        overall_signal="BULLISH",
        score=7.0,
        action="BUY",
        red_flags=[],
        positive_signals=["Strong institutional support"],
        analysis_date="2024-11-15",
    )


class TestAnalyzeInstitutionalOwnership:
    def test_basic_analysis(self):
        result = analyze_institutional_ownership(
            ticker="TEST",
            institutional_ownership_pct=75.0,
            num_holders=600,
            top10_concentration=35.0,
        )
        assert result.ticker == "TEST"
        assert result.overall_signal in ["BULLISH", "NEUTRAL", "BEARISH"]
        assert 0 <= result.score <= 10

    def test_high_ownership_bullish(self):
        result = analyze_institutional_ownership(
            ticker="TEST",
            institutional_ownership_pct=80.0,
            top10_concentration=30.0,
        )
        assert result.overall_signal == "BULLISH"
        assert result.action == "BUY"

    def test_low_ownership_bearish(self):
        result = analyze_institutional_ownership(
            ticker="TEST",
            institutional_ownership_pct=40.0,
        )
        assert result.overall_signal == "BEARISH"
        assert result.action == "SELL"

    def test_medium_ownership_neutral(self):
        result = analyze_institutional_ownership(
            ticker="TEST",
            institutional_ownership_pct=65.0,
        )
        assert result.overall_signal == "NEUTRAL"
        assert result.action == "HOLD"


class TestPromptGeneration:
    def test_generate_prompt(self, sample_result):
        prompt = generate_institutional_ownership_prompt("AAPL", sample_result)
        assert isinstance(prompt, str)
        assert "AAPL" in prompt
        assert "71.5%" in prompt
        assert "BULLISH" in prompt


class TestToDict:
    def test_to_dict(self, sample_result):
        d = sample_result.to_dict()
        assert d["ticker"] == "AAPL"
        assert d["overall_signal"] == "BULLISH"
        assert "red_flags" in d
        assert "positive_signals" in d
        assert d["institutional_ownership_pct"] == 71.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
