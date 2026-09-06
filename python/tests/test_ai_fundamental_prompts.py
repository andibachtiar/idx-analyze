"""Tests for the fundamental-analysis prompt integration module."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai.prompts.fundamental import (
    compute_score,
    generate_fundamental_prompt,
    signal_from_score,
)


class TestScoreAndSignal:
    def test_strong_company_scores_high(self):
        r = {"roe": 25.0, "debt_to_equity": 0.5, "pe_ratio": 10.0,
             "ev_ebitda": 8.0, "net_margin": 25.0, "current_ratio": 2.5}
        score = compute_score(r)
        assert score >= 6.0
        assert signal_from_score(score) == "BULLISH"

    def test_weak_company_scores_low(self):
        r = {"roe": -5.0, "debt_to_equity": 5.0, "pe_ratio": 60.0,
             "ev_ebitda": 40.0, "net_margin": -10.0, "current_ratio": 0.5}
        score = compute_score(r)
        assert score <= 2.0
        assert signal_from_score(score) == "BEARISH"

    def test_missing_data_scores_neutral(self):
        # Unavailable metrics are treated as neutral (0.5), not worst-case.
        score = compute_score({"roe": None, "debt_to_equity": None})
        assert 3.0 <= score <= 5.9
        assert signal_from_score(score) in ("NEUTRAL", "BEARISH")

    def test_signal_boundaries(self):
        assert signal_from_score(7.0) == "BULLISH"
        assert signal_from_score(5.0) == "NEUTRAL"
        assert signal_from_score(3.0) == "BEARISH"


class TestPrompt:
    def test_prompt_contains_ratios_and_signal_block(self):
        prompt = generate_fundamental_prompt(
            "BBRI",
            {"pe_ratio": 10.11, "roe": 18.57, "debt_to_equity": 4.95, "net_margin": 30.32},
            score=5.9,
            signal="NEUTRAL",
        )
        assert "BBRI" in prompt
        assert "Key Ratios" in prompt
        assert "Investment Signal" in prompt
        assert "Score: 5.9/10" in prompt
