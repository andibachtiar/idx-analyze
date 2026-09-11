"""Tests for the Phase 24 data pipeline orchestrator."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from run_pipeline import STEPS, select_by_cadence, select_steps


def _names(steps) -> list[str]:
    return [str(s["name"]) for s in steps]


def test_pipeline_starts_with_companies():
    """Companies must be first so foreign keys from other scrapers resolve."""
    assert STEPS[0]["name"] == "companies"


def test_pipeline_has_expected_kinds_of_steps():
    names = _names(STEPS)
    for expected in ["companies", "prices", "financial_ratio", "yfinance", "news_brave", "news_impacts"]:
        assert expected in names
    # Per-ticker news is now fetched on-demand during comprehensive analysis,
    # so the daily pipeline only scrapes macro news + impact tags.
    assert "news_brave_ticker" not in names


def test_select_steps_all_when_none():
    selected, unknown = select_steps(None)
    assert selected == STEPS
    assert unknown == []


def test_select_steps_subset_preserves_order():
    # "news_brave_ticker" no longer exists; it should be reported as unknown.
    selected, unknown = select_steps("news_brave_ticker,prices")
    assert unknown == ["news_brave_ticker"]
    assert _names(selected) == ["prices"]


def test_select_steps_reports_unknown():
    selected, unknown = select_steps("prices,bogus")
    assert unknown == ["bogus"]
    assert _names(selected) == ["prices"]


def test_select_by_cadence_daily_includes_core_steps():
    names = _names(select_by_cadence("daily"))
    for expected in ["companies", "prices", "financial_ratio", "news_brave", "news_impacts", "research_candidates"]:
        assert expected in names
    assert "news_brave_ticker" not in names
    assert "yfinance" not in names
    assert "financial_history" not in names


def test_select_by_cadence_all_equals_whole_pipeline():
    assert _names(select_by_cadence("all")) == _names(STEPS)
