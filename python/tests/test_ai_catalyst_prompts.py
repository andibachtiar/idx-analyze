"""Tests for Catalyst Calendar Prompt Integration (Phase 20)."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.prompts.catalyst import (
    CatalystCalendarResult,
    CatalystEvent,
    analyze_catalyst_calendar,
    generate_catalyst_prompt,
)


class TestCatalystEvent:
    def test_create_event(self):
        event = CatalystEvent(
            event_type="earnings",
            title="AAPL Earnings",
            date="2024-10-26",
            probability="High",
            bull_impact=5.0,
            bear_impact=-4.0,
        )
        assert event.event_type == "earnings"
        assert event.bull_impact == 5.0


class TestAnalyzeCatalystCalendar:
    def test_basic_analysis(self):
        result = analyze_catalyst_calendar("AAPL", look_back_days=90)
        assert result.ticker == "AAPL"
        assert len(result.events) > 0
        assert result.overall_bias in ["BULLISH", "BEARISH", "NEUTRAL"]

    def test_different_lookback(self):
        result = analyze_catalyst_calendar("MSFT", look_back_days=60)
        assert result.look_back_days == 60

    def test_empty_result(self):
        result = analyze_catalyst_calendar("TEST", look_back_days=30)
        assert result.ticker == "TEST"


class TestPromptGeneration:
    def test_generate_prompt(self):
        result = analyze_catalyst_calendar("AAPL")
        prompt = generate_catalyst_prompt("AAPL", result)
        assert isinstance(prompt, str)
        assert "AAPL" in prompt
        assert "Catalyst" in prompt or "catalyst" in prompt


class TestToDict:
    def test_to_dict(self):
        result = analyze_catalyst_calendar("GOOGL")
        d = result.to_dict()
        assert d["ticker"] == "GOOGL"
        assert "overall_bias" in d
        assert "events" in d


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
