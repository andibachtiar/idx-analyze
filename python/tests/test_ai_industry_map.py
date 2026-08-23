"""Tests for Industry Map Prompt Integration (Phase 23)."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.prompts.industry_map import (
    BottleneckAnalysis,
    ChainEdge,
    ChainLayer,
    IndustryMapResult,
    InvestmentIdea,
    PositionLocator,
    SupplyChainRisk,
    ValueMigration,
    analyze_industry_map,
    generate_industry_map_prompt,
)


@pytest.fixture
def sample_result():
    return IndustryMapResult(
        ticker="NVDA",
        theme="AI Compute Stack",
        scope="Full chain from raw materials to end users",
        layers=[
            ChainLayer(name="Raw Materials", position="Upstream", tickers=["SHECY"], concentration="Fragmented", value_capture="Low"),
            ChainLayer(name="Fab Equipment", position="Upstream", tickers=["ASML"], concentration="Monopoly", value_capture="High"),
            ChainLayer(name="Foundry", position="Midstream", tickers=["TSMC"], concentration="Oligopoly", value_capture="High"),
            ChainLayer(name="GPU/Accelerators", position="Midstream", tickers=["NVDA", "AMD"], concentration="Near-monopoly", value_capture="Very High"),
            ChainLayer(name="Cloud/CSP", position="Downstream", tickers=["AMZN", "MSFT"], concentration="Oligopoly", value_capture="Medium"),
        ],
        bottlenecks=[
            BottleneckAnalysis(layer="Fab Equipment", bottleneck_score=9.0, is_durable=True, arms_dealer_thesis="Sole EUV supplier"),
            BottleneckAnalysis(layer="GPU/Accelerators", bottleneck_score=8.5, is_durable=False, arms_dealer_thesis="CUDA lock-in"),
        ],
        value_migration=ValueMigration(
            current_pool_layer="GPU/Accelerators",
            migrating_to_layer="Cloud/CSP",
            direction="Downstream",
            trigger_event="Accelerator supply normalizes",
        ),
        risks=SupplyChainRisk(
            single_source_risks=["EUV lithography: ASML sole supplier"],
            geopolitical_exposure=["Taiwan foundry concentration"],
        ),
        investment_ideas=[
            InvestmentIdea(layer="Fab Equipment", tickers=["ASML"], rationale="Durable bottleneck toll collector", idea_type="Core/Arms Dealer", conviction="Strong"),
            InvestmentIdea(layer="GPU/Accelerators", tickers=["NVDA"], rationale="Primary beneficiary of AI compute", idea_type="Direct Winner", conviction="Moderate"),
        ],
        overall_signal="BULLISH",
        score=7.5,
        action="BUY",
        thesis_invalidators=["Chokepoint broken", "Value migrates away"],
        rerun_conditions=["Next earnings", "Price ±15%"],
    )


class TestAnalyzeIndustryMap:
    def test_basic_analysis(self):
        result = analyze_industry_map(theme="Test Theme")
        assert result.theme == "Test Theme"
        assert len(result.layers) > 0
        assert result.overall_signal in ["BULLISH", "NEUTRAL", "BEARISH"]
        assert 0 <= result.score <= 10

    def test_with_ticker(self):
        result = analyze_industry_map(ticker="NVDA", theme="AI Compute")
        assert result.ticker == "NVDA"
        assert result.position_locator is not None
        assert result.position_locator.ticker == "NVDA"

    def test_with_focus_layer(self):
        result = analyze_industry_map(theme="EV Battery", focus_layer="cathode")
        assert "cathode" in result.scope.lower()

    def test_bottleneck_detection(self):
        result = analyze_industry_map(theme="Semiconductor")
        high_bottlenecks = [b for b in result.bottlenecks if b.bottleneck_score >= 7.0]
        assert len(high_bottlenecks) >= 1

    def test_investment_ideas_generated(self):
        result = analyze_industry_map(theme="Test")
        assert len(result.investment_ideas) >= 3
        idea_types = [idea.idea_type for idea in result.investment_ideas]
        assert "Core/Arms Dealer" in idea_types

    def test_value_migration_thesis(self):
        result = analyze_industry_map(theme="Test")
        assert result.value_migration is not None
        assert result.value_migration.direction in ["Upstream", "Downstream", "Sideways"]


class TestPromptGeneration:
    def test_generate_prompt(self, sample_result):
        prompt = generate_industry_map_prompt("NVDA", "AI Compute", sample_result)
        assert isinstance(prompt, str)
        assert "NVDA" in prompt
        assert "AI Compute" in prompt
        assert "BULLISH" in prompt
        assert "```mermaid" in prompt
        assert "INVESTMENT SIGNAL" in prompt

    def test_prompt_without_ticker(self):
        result = analyze_industry_map(theme="Test Theme")
        prompt = generate_industry_map_prompt(None, "Test Theme", result)
        assert "N/A" in prompt

    def test_prompt_contains_chain_table(self, sample_result):
        prompt = generate_industry_map_prompt("NVDA", "AI Compute", sample_result)
        assert "Layer" in prompt
        assert "Position" in prompt
        assert "Concentration" in prompt


class TestToDict:
    def test_to_dict(self, sample_result):
        d = sample_result.to_dict()
        assert d["ticker"] == "NVDA"
        assert d["overall_signal"] == "BULLISH"
        assert d["score"] == 7.5
        assert d["num_layers"] == 5
        assert d["num_bottlenecks"] == 2
        assert d["investment_idea_count"] == 2


class TestModels:
    def test_chain_layer(self):
        layer = ChainLayer(name="Test", position="Upstream", tickers=["ABC"])
        assert layer.name == "Test"
        assert layer.concentration == "Fragmented"

    def test_chain_edge(self):
        edge = ChainEdge(from_layer="A", to_layer="B", dependency_strength="Sole-source", switching_cost="High")
        assert edge.from_layer == "A"
        assert edge.to_layer == "B"

    def test_position_locator(self):
        loc = PositionLocator(ticker="XYZ", primary_layer="Midstream")
        assert loc.ticker == "XYZ"
        assert loc.pricing_power_direction == "Neutral"

    def test_bottleneck_analysis(self):
        bn = BottleneckAnalysis(layer="Test", bottleneck_score=8.0, is_durable=True)
        assert bn.layer == "Test"
        assert bn.bottleneck_score == 8.0

    def test_investment_idea(self):
        idea = InvestmentIdea(layer="Test", tickers=["ABC"], rationale="Test rationale", idea_type="Core/Arms Dealer")
        assert idea.idea_type == "Core/Arms Dealer"
        assert idea.conviction == "Medium"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
