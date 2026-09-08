"""Tests for the deterministic result validator (Phase 18k)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai.prompts.validator import (
    analyze_validator,
    confidence_tier,
    enrich_with_validator,
    validate_analysis,
    validate_report,
)


def _rich_analysis() -> dict:
    return {
        "ticker": "BBCA",
        "confidence_score": 0.8,
        "overall_verdict": "BULLISH",
        "data_sources": ["fundamental_analysis", "valuation_analysis", "technical_analysis"],
        "claim_summary": {"FACT": 5, "INTERPRETATION": 3, "ASSUMPTION": 1, "SPECULATION": 1},
        "sections": {
            "executive_summary": "Summary text.",
            "business_quality": "Quality.",
            "growth_analysis": "Growth.",
            "profitability": "Profitability.",
            "financial_health": "Health.",
            "valuation": "Valuation.",
            "technical_position": "Technical.",
            "recent_events": "Events.",
            "risks": "Risk 1, risk 2, risk 3.",
            "bull_case": "Bull.",
            "base_case": "Base.",
            "bear_case": "Bear.",
            "conclusion": "Conclusion.",
        },
    }


def _empty_analysis() -> dict:
    return {"ticker": "EMPTY", "sections": {}}


class TestConfidenceTier:
    def test_tier_mapping(self):
        assert confidence_tier(85) == "VERY HIGH"
        assert confidence_tier(70) == "HIGH"
        assert confidence_tier(55) == "MEDIUM"
        assert confidence_tier(40) == "LOW"
        assert confidence_tier(20) == "VERY LOW"


class TestValidateAnalysis:
    def test_rich_analysis_scores_high(self):
        r = validate_analysis(_rich_analysis())
        assert r["total"] >= 70
        assert r["tier"] in ("HIGH", "VERY HIGH")
        assert r["dimensions"]["risk_coverage"] >= 14
        assert len(r["warnings"]) == 0 or r["total"] >= 70

    def test_empty_analysis_scores_low(self):
        r = validate_analysis(_empty_analysis())
        assert r["total"] <= 10
        assert r["tier"] == "VERY LOW"
        assert len(r["warnings"]) > 0

    def test_dimensions_present(self):
        r = validate_analysis(_rich_analysis())
        for key in ("data_quality", "methodology", "signal_consistency", "risk_coverage", "transparency"):
            assert key in r["dimensions"]


class TestValidateReport:
    def test_found_report(self, monkeypatch):
        from ai.memory import get_research_history as real_fn

        monkeypatch.setattr(
            "ai.memory.get_research_history",
            lambda ticker, limit=1: [dict(_rich_analysis(), saved_at="2026-09-08T10:00:00")],
        )
        r = validate_report("BBCA")
        assert r["found"] is True
        assert r["total"] >= 70
        assert "saved_at" in r

    def test_no_report(self, monkeypatch):
        monkeypatch.setattr(
            "ai.memory.get_research_history",
            lambda ticker, limit=1: [],
        )
        r = validate_report("NONE")
        assert r["found"] is False
        assert r["tier"] == "VERY LOW"


class TestEnrichWithValidator:
    def test_attaches_score_fields(self):
        enriched = enrich_with_validator(_rich_analysis())
        assert enriched["validator_total"] >= 70
        assert "validator_tier" in enriched
        assert "validator_dimensions" in enriched
        assert "validator_warnings" in enriched
        assert "validator_strengths" in enriched
        # Original ticker and content preserved.
        assert enriched["ticker"] == "BBCA"
        assert enriched["sections"]["conclusion"] == "Conclusion."

    def test_empty_analysis_attaches_very_low(self):
        enriched = enrich_with_validator(_empty_analysis())
        assert enriched["validator_tier"] == "VERY LOW"
        assert enriched["validator_total"] <= 10

    def test_does_not_mutate_input(self):
        original = _rich_analysis()
        before = dict(original)
        enrich_with_validator(original)
        assert list(original.keys()) == list(before.keys())
        assert "validator_total" not in original


class TestAnalyzeValidator:
    def test_deterministic_no_llm(self, monkeypatch):
        monkeypatch.setattr(
            "ai.memory.get_research_history",
            lambda ticker, limit=1: [dict(_rich_analysis(), saved_at="2026-09-08T10:00:00")],
        )
        result = analyze_validator(ticker="BBCA")
        assert result["ticker"] == "BBCA"
        assert result["llm_used"] is False
        assert result["total"] >= 70
        assert "llm_analysis" not in result
