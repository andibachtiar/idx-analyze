"""Tests for the Phase 24 data pipeline orchestrator."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from run_pipeline import STEPS, select_steps


def _names(steps) -> list[str]:
    return [str(s["name"]) for s in steps]


def test_pipeline_starts_with_companies():
    """Companies must be first so foreign keys from other scrapers resolve."""
    assert STEPS[0]["name"] == "companies"


def test_pipeline_has_expected_kinds_of_steps():
    names = _names(STEPS)
    for expected in ["companies", "prices", "financial_ratio", "yfinance", "news", "news_link"]:
        assert expected in names


def test_select_steps_all_when_none():
    selected, unknown = select_steps(None)
    assert selected == STEPS
    assert unknown == []


def test_select_steps_subset_preserves_order():
    selected, unknown = select_steps("news,prices")
    assert unknown == []
    # Order follows the canonical pipeline order, not the input order.
    assert _names(selected) == ["prices", "news"]


def test_select_steps_reports_unknown():
    selected, unknown = select_steps("prices,bogus")
    assert unknown == ["bogus"]
    assert _names(selected) == ["prices"]
