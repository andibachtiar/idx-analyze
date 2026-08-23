"""Tests for Competitor Analysis Prompt Integration (Phase 21)."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.prompts.competitor import (
    CompetitorAnalysisResult,
    CompetitorBenchmark,
    FiveForcesScore,
    MoatSource,
    analyze_competitor_position,
    generate_competitor_prompt,
)


class TestMoatSource:
    def test_create_moat_source(self):
        source = MoatSource(name="Network Effects", strength="Strong")
        assert source.name == "Network Effects"
        assert source.strength == "Strong"


class TestFiveForcesScore:
    def test_industry_attractiveness(self):
        score = FiveForcesScore(
            competitive_rivalry=4,
            new_entrant_threat=2,
            supplier_power=2,
            buyer_power=2,
            substitute_threat=2,
        )
        # Higher scores for rivalry, lower for threats = more attractive
        assert score.industry_attractiveness > 0
        assert score.industry_attractiveness <= 5


class TestAnalyzeCompetitorPosition:
    def test_basic_analysis(self):
        result = analyze_competitor_position("AAPL", moat_width="Wide", moat_score=8.0)
        assert result.ticker == "AAPL"
        assert result.moat_width == "Wide"
        assert result.overall_signal in ["BULLISH", "NEUTRAL", "BEARISH"]

    def test_narrow_moat(self):
        result = analyze_competitor_position("TEST", moat_width="Narrow", moat_score=4.0)
        assert result.overall_signal in ["BULLISH", "NEUTRAL", "BEARISH"]

    def test_no_moat(self):
        result = analyze_competitor_position("COMMD", moat_width="None", moat_score=3.0)
        assert result.moat_width == "None"


class TestPromptGeneration:
    def test_generate_prompt(self):
        result = analyze_competitor_position("MSFT", moat_score=7.0)
        prompt = generate_competitor_prompt("MSFT", result)
        assert isinstance(prompt, str)
        assert "MSFT" in prompt
        assert "Moat" in prompt or "moat" in prompt


class TestToDict:
    def test_to_dict(self):
        result = analyze_competitor_position("GOOGL", moat_score=6.0)
        d = result.to_dict()
        assert d["ticker"] == "GOOGL"
        assert "moat_width" in d
        assert "overall_signal" in d


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
