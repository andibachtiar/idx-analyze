"""Tests for deterministic macro/impact interpretation (Fase B4)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai.prompts import macro_impact as mi


class TestBuildSnapshot:
    def test_aggregates_direction_counts_and_tickers(self):
        impacts = [
            {"sector": "Keuangan", "direction": "positive", "confidence": 0.8, "ticker": "BBCA", "title": "Rates up", "url": "u1"},
            {"sector": "Keuangan", "direction": "negative", "confidence": 0.6, "ticker": "BBRI", "title": "NPL up", "url": "u2"},
            {"sector": "Energi", "direction": "positive", "confidence": 0.7, "ticker": None, "title": "Oil up", "url": "u3"},
        ]
        snap = mi.build_snapshot(impacts)
        sectors = {s["sector"]: s for s in snap["sectors"]}
        keu = sectors["Keuangan"]
        assert keu["positive_count"] == 1
        assert keu["negative_count"] == 1
        assert set(keu["affected_tickers"]) == {"BBCA", "BBRI"}
        assert keu["positive_confidence"] == 0.8
        assert keu["negative_confidence"] == 0.6

    def test_ranks_by_magnitude_of_net_strength(self):
        # Energi strongly positive, Keuangan strongly negative -> both appear, ranking stable.
        impacts = [
            {"sector": "Energi", "direction": "positive", "confidence": 0.9, "ticker": None, "title": "t", "url": "u"},
            {"sector": "Keuangan", "direction": "negative", "confidence": 0.9, "ticker": None, "title": "t", "url": "u"},
        ]
        snap = mi.build_snapshot(impacts)
        sectors = [s["sector"] for s in snap["sectors"]]
        assert set(sectors) == {"Energi", "Keuangan"}
        # Both abs(net) == 0.9; ties broken by total volume.
        assert snap["sectors"][0]["sector"] in ("Energi", "Keuangan")

    def test_empty_impacts_returns_empty(self):
        assert mi.build_snapshot([])["sectors"] == []


class TestBuildPrompt:
    def test_prompt_contains_deterministic_evidence(self):
        impacts = [
            {"sector": "Energi", "direction": "positive", "confidence": 0.9, "ticker": "ADRO", "title": "Oil price up", "url": "u"}
        ]
        snap = mi.build_snapshot(impacts)
        prompt = mi.build_prompt(snap)
        assert "Energi" in prompt
        assert "ADRO" in prompt
        assert "Oil price up" in prompt
        assert "do not invent" in prompt.lower()

    def test_prompt_accepts_focus(self):
        snap = {"generated_at": "2026-09-05T00:00:00", "sectors": []}
        prompt = mi.build_prompt(snap, focus="Which sectors most at risk?")
        assert "Which sectors most at risk" in prompt

    def test_includes_keywords_and_guidance(self):
        impacts = [
            {"sector": "Keuangan", "direction": "positive", "confidence": 0.8,
             "ticker": None, "title": "BI rupiah IHSG", "url": "u", "geo": "domestic",
             "matched_keywords": "kenaikan suku bunga, naikkan suku bunga"},
        ]
        snap = mi.build_snapshot(impacts)
        prompt = mi.build_prompt(snap)
        assert "kenaikan suku bunga" in prompt
        assert "## Keyword transparency" in prompt
        assert "## Guidance on geographic origin" in prompt


class TestClassifyGeo:
    def test_domestic_hints(self):
        assert mi.classify_geo("IHSG menguat, Bank Indonesia tahan suku bunga rupiah") == "domestic"

    def test_global_hints(self):
        assert mi.classify_geo("ECB: prospek kenaikan suku bunga", "FXStreet") == "global"
        assert mi.classify_geo("The Fed menaikkan suku bunga di September") == "global"

    def test_mixed_hints(self):
        assert mi.classify_geo("The Fed dan Bank Indonesia rupiah") == "mixed"

    def test_unknown_when_no_hints(self):
        assert mi.classify_geo("Perusahaan mencatat laba naik") == "unknown"


class TestGeoWeight:
    def test_weights_are_deterministic(self):
        assert mi.geo_weight("domestic") == 1.0
        assert mi.geo_weight("global") == 0.5
        assert mi.geo_weight("mixed") == 0.75
        assert mi.geo_weight("unknown") == 1.0

    def test_domestic_outranks_global_at_equal_confidence(self):
        impacts = [
            {"sector": "Keuangan", "direction": "positive", "confidence": 0.8,
             "ticker": None, "title": "BI rupiah IHSG", "url": "u", "geo": "domestic"},
            {"sector": "Energi", "direction": "positive", "confidence": 0.8,
             "ticker": None, "title": "ECB Fed global", "url": "u", "geo": "global"},
        ]
        snap = mi.build_snapshot(impacts)
        sectors = {s["sector"]: s for s in snap["sectors"]}
        assert sectors["Keuangan"]["net_strength"] == 0.8
        assert sectors["Energi"]["net_strength"] == 0.4
        assert sectors["Keuangan"]["domestic_share"] == 1.0
        assert sectors["Energi"]["domestic_share"] == 0.0


class TestNetBaseline:
    def test_median_and_percentile_over_days(self):
        hist = [
            {"sector": "Keuangan", "direction": "positive", "confidence": 0.8,
             "geo": "domestic", "published_at": "2026-09-01T10:00:00"},
            {"sector": "Keuangan", "direction": "positive", "confidence": 0.6,
             "geo": "global", "published_at": "2026-09-02T10:00:00"},
            {"sector": "Keuangan", "direction": "positive", "confidence": 0.4,
             "geo": "global", "published_at": "2026-09-03T10:00:00"},
        ]
        b = mi.compute_net_baselines(hist, current_sectors={"Keuangan": 0.7})
        keu = b["Keuangan"]
        # day1: 0.8*1.0=0.8, day2: 0.6*0.5=0.3, day3: 0.4*0.5=0.2
        assert keu["median"] == 0.3
        assert keu["sample_days"] == 3
        assert keu["current"] == 0.7
        # min_sample_days default 5 -> insufficient, confidence < 1
        assert keu["sample_sufficient"] is False
        assert keu["baseline_confidence"] < 1.0

    def test_sufficient_sample_marks_confidence_1(self):
        hist = [
            {"sector": "Keuangan", "direction": "positive", "confidence": 0.5,
             "geo": "global", "published_at": f"2026-09-{i:02d}T10:00:00"}
            for i in range(1, 7)
        ]
        b = mi.compute_net_baselines(hist, min_sample_days=5)
        keu = b["Keuangan"]
        assert keu["sample_days"] == 6
        assert keu["sample_sufficient"] is True
        assert keu["baseline_confidence"] == 1.0

    def test_attach_baselines_adds_field(self):
        snap = {"sectors": [{"sector": "Keuangan", "net_strength": 0.4}]}
        baselines = {"Keuangan": {"median": 0.3, "p90": 0.8, "sample_days": 5, "current": 0.4}}
        mi.attach_baselines(snap, baselines)
        assert snap["sectors"][0]["baseline"]["median"] == 0.3


class TestAnalyze:
    def test_returns_deterministic_snapshot_without_llm(self, monkeypatch):
        monkeypatch.setattr(
            mi,
            "load_impacts",
            lambda hours=48, limit=200: [
                {"sector": "Energi", "direction": "positive", "confidence": 0.8, "ticker": None, "title": "t", "url": "u"}
            ],
        )
        out = mi.analyze_macro_impacts(use_llm=False)
        assert out["total_impact_tags"] == 1
        assert out["llm_used"] is False
        assert out["llm_analysis"] == ""
        assert out["sectors"][0]["sector"] == "Energi"


class TestBuildCandidates:
    def _snapshot(self):
        return {
            "generated_at": "2026-09-05T00:00:00",
            "sectors": [
                {
                    "sector": "Keuangan",
                    "positive_count": 5,
                    "negative_count": 0,
                    "positive_confidence": 0.74,
                    "negative_confidence": 0.0,
                    "net_strength": 3.7,
                    "affected_tickers": ["BBCA", "BBRI"],
                    "news": [],
                },
                {
                    "sector": "Properti & Real Estat",
                    "positive_count": 0,
                    "negative_count": 5,
                    "positive_confidence": 0.0,
                    "negative_confidence": 0.66,
                    "net_strength": -3.3,
                    "affected_tickers": [],
                    "news": [],
                },
                {
                    "sector": "Kesehatan",
                    "positive_count": 1,
                    "negative_count": 1,
                    "positive_confidence": 0.1,
                    "negative_confidence": 0.1,
                    "net_strength": 0.0,  # below min -> excluded
                    "affected_tickers": [],
                    "news": [],
                },
            ],
        }

    def test_emits_sector_and_ticker_candidates_for_pressured_sectors(self):
        cands = mi.build_candidates(self._snapshot(), min_abs_net=0.5)
        keys = {(c["sector"], c["ticker"]) for c in cands}
        # Keuangan: sector level + BBCA + BBRI
        assert ("Keuangan", None) in keys
        assert ("Keuangan", "BBCA") in keys
        assert ("Keuangan", "BBRI") in keys
        # Properti: only sector level (no tickers)
        assert ("Properti & Real Estat", None) in keys
        # Low-pressure sector excluded
        assert not any(c["sector"] == "Kesehatan" for c in cands)

    def test_direction_and_confidence_follow_dominant_pressure(self):
        cands = mi.build_candidates(self._snapshot())
        keu = next(c for c in cands if c["sector"] == "Keuangan" and c["ticker"] == "BBCA")
        assert keu["direction"] == "positive"
        assert keu["confidence"] == 0.74
        prop = next(c for c in cands if c["sector"] == "Properti & Real Estat" and c["ticker"] is None)
        assert prop["direction"] == "negative"
        assert prop["confidence"] == 0.66

    def test_generate_research_candidates_carries_deterministic_list(self, monkeypatch):
        monkeypatch.setattr(mi, "load_impacts", lambda hours=48, limit=200: [])
        out = mi.generate_research_candidates(use_llm=False)
        assert "candidates" in out
        assert isinstance(out["candidates"], list)
        # With no impacts there are no pressured sectors -> no candidates.
        assert out["candidates"] == []

    def test_low_net_filter_drops_sector(self):
        snap = self._snapshot()
        # Raise the threshold so even the 3.7/3.3 sectors get dropped.
        assert mi.build_candidates(snap, min_abs_net=10.0) == []

    def test_expands_sector_to_liquid_tickers_capped(self):
        sector_tickers = {
            "Keuangan": ["BBCA", "BBRI", "BMRI", "BBNI", "BBHI", "BRIS"],
            "Properti & Real Estat": ["DMAS", "KIJA"],
        }
        cands = mi.build_candidates(
            self._snapshot(), sector_tickers=sector_tickers, max_tickers_per_sector=3
        )
        keu_tickers = [c["ticker"] for c in cands if c["sector"] == "Keuangan" and c["ticker"]]
        # Real tagged tickers (BBCA, BBRI) kept first, then liquid names up to cap.
        assert "BBCA" in keu_tickers
        assert "BBRI" in keu_tickers
        # Cap includes the 2 tagged + fills to 3 from the liquid map.
        assert len(keu_tickers) == 3
        # Properti sector expanded even though affected_tickers was empty.
        prop_tickers = [c["ticker"] for c in cands if c["sector"] == "Properti & Real Estat" and c["ticker"]]
        assert set(prop_tickers) == {"DMAS", "KIJA"}

    def test_generate_expands_via_loader_capped(self, monkeypatch):
        monkeypatch.setattr(
            mi,
            "load_impacts",
            lambda hours=48, limit=200: [
                {"sector": "Keuangan", "direction": "positive", "confidence": 0.8,
                 "ticker": None, "title": "t", "url": "u"}
            ],
        )
        fake_loader = type("L", (), {"get_sector_tickers": lambda self, s, limit=5: ["BBCA", "BBRI"]})()
        monkeypatch.setattr(mi, "get_data_loader", lambda: fake_loader)
        out = mi.generate_research_candidates(use_llm=False, max_tickers_per_sector=2)
        keu_tickers = [c["ticker"] for c in out["candidates"] if c.get("ticker")]
        assert set(keu_tickers) == {"BBCA", "BBRI"}
