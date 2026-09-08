"""Tests for periodic auto-analysis recency guard (Phase 17)."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import auto_analyze as aa


class _Report:
    """Minimal ResearchReport stand-in with the fields the dict mapper reads."""

    def __init__(self):
        self.ticker = "BBCA"
        self.question = ""
        self.timestamp = None
        self.confidence = 0.5
        self.executive_summary = "e"
        self.business_quality = "b"
        self.growth_analysis = "g"
        self.profitability = "p"
        self.financial_health = "f"
        self.valuation = "v"
        self.technical_position = "t"
        self.recent_events = "r"
        self.risks = "k"
        self.bull_case = "bu"
        self.base_case = "ba"
        self.bear_case = "be"
        self.conclusion = "c"


class _FakeMemory:
    def __init__(self, latest=None):
        self.latest = latest

    def get_latest_report(self, ticker):
        return self.latest


def _saved(hours_ago: float) -> dict:
    when = datetime.now().astimezone() - timedelta(hours=hours_ago)
    return {"saved_at": when.isoformat(), "ticker": "BBCA"}


class TestAnalyzeTicker:
    def test_skips_recent_report(self, monkeypatch):
        monkeypatch.setattr(aa, "ResearchMemory", lambda: _FakeMemory(_saved(1)))
        called = []
        monkeypatch.setattr(aa, "analyze_stock", lambda t, question="": called.append(t) or _Report())
        r = aa.analyze_ticker("BBCA", min_hours=24)
        assert r["status"] == "skipped"
        assert called == []  # LLM not hit again

    def test_analyzes_stale_report(self, monkeypatch):
        monkeypatch.setattr(aa, "ResearchMemory", lambda: _FakeMemory(_saved(48)))
        called = []
        saved = {}
        monkeypatch.setattr(aa, "analyze_stock", lambda t, question="": called.append(t) or _Report())
        monkeypatch.setattr(aa, "save_research_report", lambda t, r, question="", storage_path=None: saved.__setitem__("t", t) or "path")
        r = aa.analyze_ticker("BBCA", min_hours=24)
        assert r["status"] == "analyzed"
        assert called == ["BBCA"]
        assert saved["t"] == "BBCA"

    def test_force_ignores_guard(self, monkeypatch):
        monkeypatch.setattr(aa, "ResearchMemory", lambda: _FakeMemory(_saved(1)))
        called = []
        monkeypatch.setattr(aa, "analyze_stock", lambda t, question="": called.append(t) or _Report())
        monkeypatch.setattr(aa, "save_research_report", lambda t, r, question="", storage_path=None: "p")
        r = aa.analyze_ticker("BBCA", min_hours=24, force=True)
        assert r["status"] == "analyzed"
        assert called == ["BBCA"]


class TestReportToDict:
    def test_maps_structured_fields(self):
        d = aa.report_to_dict(_Report())
        assert d["ticker"] == "BBCA"
        assert d["sections"]["executive_summary"] == "e"
        assert d["sections"]["valuation"] == "v"
        assert d["confidence_score"] == 0.5

    def test_produces_sections_container(self):
        """Report saved by the pipeline uses the same sections structure as the API."""
        d = aa.report_to_dict(_Report())
        for key in (
            "executive_summary", "business_quality", "growth_analysis",
            "profitability", "financial_health", "valuation",
            "technical_position", "recent_events", "risks", "bull_case",
            "base_case", "bear_case", "conclusion",
        ):
            assert key in d["sections"]
        assert d["overall_verdict"] == ""


class TestRun:
    def test_dry_run_plans_without_analyzing(self, monkeypatch):
        monkeypatch.setattr(aa, "resolve_tickers", lambda source="favorites", limit=None: ["BBCA", "BBRI"])
        out = aa.run(force=True, dry_run=True)
        assert out == 0

    def test_research_candidates_source(self, monkeypatch):
        """source=research_candidates uses resolve_research_candidate_tickers."""
        monkeypatch.setattr(aa, "resolve_research_candidate_tickers", lambda limit=None: ["EMAS", "MINE"])
        assert aa.resolve_tickers(source="research_candidates") == ["EMAS", "MINE"]

    def test_research_candidates_default_guard_is_one_week(self, monkeypatch):
        """Comprehensive analysis defaults to a 1-week (168h) recency guard."""
        monkeypatch.delenv("RESEARCH_ANALYZE_MIN_HOURS", raising=False)
        monkeypatch.delenv("AUTO_ANALYZE_MIN_HOURS", raising=False)
        monkeypatch.setattr(aa, "resolve_tickers", lambda source="favorites", limit=None: ["EMAS"])
        captured = {}
        monkeypatch.setattr(
            aa, "analyze_ticker",
            lambda t, min_hours=0.0, force=False, question="": (captured.__setitem__("min_hours", min_hours), {"status": "analyzed"})[1],
        )
        aa.run(source="research_candidates", force=True)
        assert captured["min_hours"] == 168

    def test_favorites_default_guard_is_24h(self, monkeypatch):
        """Favorites sensitivity guard stays at 24h by default."""
        monkeypatch.delenv("RESEARCH_ANALYZE_MIN_HOURS", raising=False)
        monkeypatch.delenv("AUTO_ANALYZE_MIN_HOURS", raising=False)
        monkeypatch.setattr(aa, "resolve_tickers", lambda source="favorites", limit=None: ["BBCA"])
        captured = {}
        monkeypatch.setattr(
            aa, "analyze_ticker",
            lambda t, min_hours=0.0, force=False, question="": (captured.__setitem__("min_hours", min_hours), {"status": "analyzed"})[1],
        )
        aa.run(source="favorites", force=True)
        assert captured["min_hours"] == 24
