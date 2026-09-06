"""Tests for deterministic news -> sector/ticker impact tagging (Fase B3)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import enrich_news_impacts as e


class TestDetectImpacts:
    def test_suku_bunga_naik_tags_keuangan_positive(self):
        impacts = e.detect_impacts("Bank Indonesia menaikkan suku bunga acuan 25 bps.")
        keuangan = [i for i in impacts if i["sector"] == "Keuangan" and i["direction"] == "positive"]
        assert keuangan, impacts

    def test_suku_bunga_naik_also_hurts_property(self):
        # Same driver can be positive for banks and negative for property.
        impacts = e.detect_impacts("BI menaikkan suku bunga, membebani sektor properti.")
        directions = {(i["sector"], i["direction"]) for i in impacts}
        assert ("Keuangan", "positive") in directions
        assert ("Properti & Real Estat", "negative") in directions

    def test_commodity_direction(self):
        assert any(
            i["sector"] == "Energi" and i["direction"] == "positive"
            for i in e.detect_impacts("harga batubara naik di pasar global")
        )
        assert any(
            i["sector"] == "Energi" and i["direction"] == "negative"
            for i in e.detect_impacts("harga minyak dunia turun tajam")
        )

    def test_confidence_rises_with_more_signals(self):
        low = e.detect_impacts("harga batubara naik")
        high = e.detect_impacts("harga batubara naik dan harga minyak dunia naik bersama")
        low_conf = next(i["confidence"] for i in low if i["sector"] == "Energi")
        high_conf = next(i["confidence"] for i in high if i["sector"] == "Energi")
        assert high_conf > low_conf
        assert 0.0 < low_conf <= 0.95

    def test_empty_text_returns_no_impacts(self):
        assert e.detect_impacts("") == []
        assert e.detect_impacts(" ") == []

    def test_no_match_returns_empty(self):
        assert e.detect_impacts("cuaca cerah di pantai") == []


class TestImpactRows:
    def test_default_is_sector_level_only(self):
        """Default: one sector-level row for general news, no explosion into every ticker."""
        impact = {"sector": "Keuangan", "direction": "positive", "confidence": 0.6, "matched_keywords": ["suku bunga naik"]}
        rows = e._impact_rows(1, impact, None, {"Keuangan": ["BMRI", "BBRI", "BBCA"]})
        assert rows == [(1, "Keuangan", None, "positive", 0.6, "suku bunga naik")]

    def test_expand_writes_all_sector_tickers(self):
        """--expand materializes one row per company in the impacted sector."""
        impact = {"sector": "Keuangan", "direction": "positive", "confidence": 0.6, "matched_keywords": ["suku bunga naik"]}
        rows = e._impact_rows(1, impact, None, {"Keuangan": ["BMRI", "BBRI", "BBCA"]}, expand=True)
        assert (1, "Keuangan", None, "positive", 0.6, "suku bunga naik") in rows
        assert (1, "Keuangan", "BMRI", "positive", 0.6, "suku bunga naik") in rows
        assert len(rows) == 1 + 3

    def test_article_ticker_used_instead_of_expansion(self):
        """A company-specific article tags its own ticker (and the sector level)."""
        impact = {"sector": "Keuangan", "direction": "positive", "confidence": 0.6, "matched_keywords": []}
        rows = e._impact_rows(1, impact, "BBCA", {"Keuangan": ["BMRI", "BBRI", "BBCA"]})
        tickers = [r[2] for r in rows]
        assert None in tickers  # sector-level
        assert "BBCA" in tickers
        assert "BMRI" not in tickers  # no expansion without --expand

    def test_expand_with_article_ticker_does_not_expand(self):
        """Even with --expand, a named ticker article is not expanded to the whole sector."""
        impact = {"sector": "Energi", "direction": "positive", "confidence": 0.6, "matched_keywords": []}
        rows = e._impact_rows(1, impact, "ADRO", {"Energi": ["ADRO", "PTBA", "ITMG"]}, expand=True)
        tickers = [r[2] for r in rows]
        assert tickers.count("ADRO") == 1
        assert "PTBA" not in tickers
