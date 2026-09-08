"""Tests for deterministic dividend-quality analysis (adapted dividend-analysis)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai.prompts.dividend import (
    _grade,
    analyze_dividend,
    dividend_ratios,
    safety_score,
    yield_trap_check,
)


def _fake_loader(ratios: dict):
    """Return a fake data loader exposing get_financial_ratios_merged."""
    from ai.data_loader_pg import PostgreSQLDataLoader

    class _Loader(PostgreSQLDataLoader):
        def get_financial_ratios_merged(self, ticker):
            return dict(ratios)

    return _Loader()


class TestSafetyScore:
    def test_safe_profile_scores_high(self):
        r = {
            "payout_ratio": 35.0,
            "debt_to_equity": 0.4,
            "interest_coverage": 8.0,
            "earnings_cagr": 12.0,
        }
        score, grade, assessment = safety_score(r)
        assert score == 100.0
        assert grade == "A+"
        assert assessment == "Very Safe"

    def test_high_payout_low_grade(self):
        r = {
            "payout_ratio": 90.0,
            "debt_to_equity": 2.0,
            "interest_coverage": 1.5,
            "earnings_cagr": -5.0,
        }
        score, grade, _ = safety_score(r)
        assert score < 30
        assert grade == "F"

    def test_missing_data_scores_zero_without_guessing(self):
        score, grade, _ = safety_score({
            "payout_ratio": None,
            "debt_to_equity": None,
            "interest_coverage": None,
            "earnings_cagr": None,
        })
        assert score == 0.0
        assert grade == "F"

    def test_grade_mapping(self):
        assert _grade(92) == ("A+", "Very Safe")
        assert _grade(78) == ("A", "Safe")
        assert _grade(62) == ("B", "Borderline Safe")
        assert _grade(50) == ("C", "Elevated Risk")
        assert _grade(35) == ("D", "Unsafe")
        assert _grade(20) == ("F", "Danger Zone")


class TestYieldTrap:
    def test_yield_over_seven_is_high(self):
        risk, flags = yield_trap_check({"dividend_yield": 8.0, "payout_ratio": 45.0, "earnings_cagr": 10.0})
        assert risk == "high"
        assert any("7%" in f for f in flags)

    def test_high_yield_and_high_payout_is_high(self):
        risk, _ = yield_trap_check({"dividend_yield": 5.0, "payout_ratio": 75.0, "earnings_cagr": 5.0})
        assert risk == "high"

    def test_low_yield_no_trap(self):
        risk, _ = yield_trap_check({"dividend_yield": 2.0, "payout_ratio": 40.0, "earnings_cagr": 8.0})
        assert risk == "none"


class TestDividendRatios:
    def test_reads_merged_ratios(self, monkeypatch):
        ratios = {
            "dividend_yield": 6.5,
            "payout_ratio": 45.0,
            "fcf_margin": 18.0,
            "earnings_cagr": 9.0,
            "debt_to_equity": 0.6,
            "current_ratio": 1.5,
            "interest_coverage": 6.0,
        }
        monkeypatch.setattr("ai.prompts.dividend.get_data_loader", lambda: _fake_loader(ratios))
        r = dividend_ratios("BBRI")
        assert r == ratios


class TestAnalyzeDividend:
    def test_deterministic_snapshot_no_llm(self, monkeypatch):
        ratios = {
            "dividend_yield": 5.2,
            "payout_ratio": 45.0,
            "fcf_margin": 20.0,
            "earnings_cagr": 10.0,
            "debt_to_equity": 0.5,
            "current_ratio": 1.8,
            "interest_coverage": 7.0,
        }
        monkeypatch.setattr("ai.prompts.dividend.get_data_loader", lambda: _fake_loader(ratios))
        result = analyze_dividend("BBRI")
        assert result["ticker"] == "BBRI"
        assert result["has_data"] is True
        assert result["llm_used"] is False
        assert result["safety_score"] > 0
        assert result["metrics"] == ratios
        assert "llm_analysis" not in result

    def test_missing_data_flagged(self, monkeypatch):
        monkeypatch.setattr("ai.prompts.dividend.get_data_loader", lambda: _fake_loader({}))
        result = analyze_dividend("EMPTY")
        assert result["has_data"] is False
        assert result["yield_trap_risk"] == "none"
        assert any("not available" in n for n in result["notes"])
