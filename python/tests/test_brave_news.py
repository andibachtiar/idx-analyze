"""Tests for the Brave Search news scraper (Fase A)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import scrape_brave_news as s


class TestQuery:
    def test_build_query_contains_ticker(self):
        q = s.build_query("BBCA")
        assert "BBCA" in q
        assert "berita" in q.lower() or "news" in q.lower()


class TestNormalize:
    def test_normalize_item_maps_fields(self):
        item = {
            "title": "Bank BRI laba naik",
            "url": "https://cnbcindonesia.com/news/1",
            "description": "Laba bersih naik 12%",
            "page_age": "2026-09-01T10:00:00Z",
            "profile": {"name": "CNBC Indonesia", "url": "https://cnbcindonesia.com"},
            "meta_url": {"hostname": "cnbcindonesia.com"},
        }
        rec = s.normalize_item(item, "BBCA")
        assert rec is not None
        assert rec["ticker"] == "BBCA"
        assert rec["title"] == "Bank BRI laba naik"
        assert rec["url"] == "https://cnbcindonesia.com/news/1"
        assert rec["source"] == "CNBC Indonesia"
        assert rec["publishedAt"] == "2026-09-01T10:00:00Z"
        # Deterministic dedup key.
        assert len(rec["newsCode"]) == 40

    def test_normalize_uses_profile_and_meta(self):
        # Brave real shape: source is profile.name / meta_url.hostname.
        item = {
            "title": "BMRI bagi dividen interim",
            "url": "https://fxstreet-id.com/news/bmri-...",
            "description": "...",
            "page_age": "2026-09-04T07:15:13",
            "profile": {"name": "FXStreet"},
            "meta_url": {"hostname": "fxstreet-id.com"},
        }
        rec = s.normalize_item(item, "BMRI")
        assert rec is not None
        assert rec["source"] == "FXStreet"
        assert rec["publishedAt"] == "2026-09-04T07:15:13"

    def test_normalize_item_requires_title_and_url(self):
        assert s.normalize_item({"title": "x"}, "BBCA") is None
        assert s.normalize_item({"url": "https://x"}, "BBCA") is None


class TestSourceFilter:
    def test_source_allowed_empty_allowlist_accepts_all(self):
        item = {"profile": {"name": "Random Blog"}}
        assert s.source_allowed(item, []) is True

    def test_source_allowed_matches_domain_from_meta(self):
        item = {"meta_url": {"hostname": "cnbcindonesia.com"}, "profile": {"name": "CNBC Indonesia"}}
        assert s.source_allowed(item, ["cnbcindonesia.com"]) is True
        assert s.source_allowed(item, ["katadata.co.id"]) is False

    def test_source_allowed_matches_publisher_name(self):
        item = {"profile": {"name": "Bloomberg Technoz"}, "meta_url": {"hostname": "bloombergtechnoz.com"}}
        assert s.source_allowed(item, ["bloombergtechnoz.com"]) is True
        assert s.source_allowed(item, ["bloombergtechnoz"]) is True

    def test_source_allowed_rejects_missing_source_when_filter_on(self):
        assert s.source_allowed({"title": "x"}, ["cnbcindonesia.com"]) is False


class TestStableHash:
    def test_news_code_deterministic(self):
        a = s._stable_hash("https://x.test/a")
        b = s._stable_hash("https://x.test/a")
        assert a == b
        assert len(a) == 40
        assert "hash(" not in a  # not builtin hash() (non-deterministic)


class TestFetch:
    def test_fetch_reads_results_key(self, monkeypatch):
        """Brave News returns items under top-level ``results`` (not ``news``)."""
        from unittest.mock import MagicMock
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        item = {"title": "x", "url": "https://x", "page_age": "2026-09-05T00:00:00"}
        fake_resp.json.return_value = {"type": "news", "results": [item]}

        monkeypatch.setattr(s.requests, "get", lambda *a, **kw: fake_resp)
        cfg = {"api_key": "k", "url": "https://x", "count": 5, "country": "id", "lang": "", "sources": []}
        out = s.fetch_brave_news(cfg, "BBCA saham berita")
        assert out == [item]

    def test_fetch_falls_back_to_news_key(self, monkeypatch):
        """Fallback for APIs that still return items under ``news``."""
        from unittest.mock import MagicMock
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        item = {"title": "x", "url": "https://x"}
        fake_resp.json.return_value = {"news": [item]}

        monkeypatch.setattr(s.requests, "get", lambda *a, **kw: fake_resp)
        cfg = {"api_key": "k", "url": "https://x", "count": 5, "country": "id", "lang": "", "sources": []}
        out = s.fetch_brave_news(cfg, "BBCA saham berita")
        assert out == [item]

    def test_fetch_does_not_send_source_param(self, monkeypatch):
        """/res/v1/news/search rejects a 'source' param (HTTP 422), so it must not be sent."""
        from unittest.mock import MagicMock
        captured = {}
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"results": []}

        def fake_get(url, params=None, headers=None, timeout=20, impersonate=None):
            captured["params"] = params
            captured["headers"] = headers
            return fake_resp

        monkeypatch.setattr(s.requests, "get", fake_get)
        cfg = {"api_key": "k", "url": "https://x", "count": 5, "country": "id", "lang": "id", "sources": []}
        s.fetch_brave_news(cfg, "BBCA saham berita")
        assert "source" not in captured["params"]
        assert captured["headers"]["X-Subscription-Token"] == "k"
        assert captured["params"]["q"] == "BBCA saham berita"

    def test_fetch_omits_search_lang_when_empty(self, monkeypatch):
        """search_lang=id is rejected by Brave (422) so it must be omitted when unset."""
        from unittest.mock import MagicMock
        captured = {}
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"news": []}

        def fake_get(url, params=None, headers=None, timeout=20, impersonate=None):
            captured["params"] = params
            return fake_resp

        monkeypatch.setattr(s.requests, "get", fake_get)
        cfg = {"api_key": "k", "url": "https://x", "count": 5, "country": "id", "lang": "", "sources": []}
        s.fetch_brave_news(cfg, "BBCA saham berita")
        assert "search_lang" not in captured["params"]
        # country=id IS valid for Brave's country param, so it is preserved.
        assert captured["params"]["country"] == "id"

    def test_fetch_sends_freshness_only_when_set(self, monkeypatch):
        """freshness should be purely optional and omitted when not configured."""
        from unittest.mock import MagicMock

        def run(freshness):
            captured = {}
            fake_resp = MagicMock()
            fake_resp.status_code = 200
            fake_resp.json.return_value = {"news": []}

            def fake_get(url, params=None, headers=None, timeout=20, impersonate=None):
                captured["params"] = params
                return fake_resp

            monkeypatch.setattr(s.requests, "get", fake_get)
            cfg = {"api_key": "k", "url": "https://x", "count": 5, "country": "id", "lang": "", "sources": [], "freshness": freshness}
            s.fetch_brave_news(cfg, "BBCA saham berita")
            return captured["params"]

        assert "freshness" not in run("")
        assert run("pw")["freshness"] == "pw"
        assert run("pm")["freshness"] == "pm"


class _FakeStore:
    """Minimal context manager stand-in for ScraperDatabase in macro tests."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _CaptureStore(_FakeStore):
    """Fake store that records inserted news and serves company names."""

    def __init__(self, names=None):
        self.inserted = []
        self._names = names or {}

    def get_company_names(self, tickers):
        return {str(t).upper(): self._names.get(str(t).upper(), str(t).upper()) for t in tickers}

    def insert_news(self, records):
        records = list(records)
        self.inserted.extend(records)
        return len(records)


class TestRelevanceGate:
    """Brave tags every result with the query ticker; the gate must drop the
    unrelated ones (backlog #3)."""

    def _cfg(self):
        return {"count": 5, "country": "id", "lang": "", "sources": []}

    def _item(self, title):
        return {
            "title": title,
            "url": "https://investing.com/" + title.lower().replace(" ", "-")[:40],
            "description": "",
            "profile": {"name": "Investing.com"},
            "meta_url": {"hostname": "investing.com"},
        }

    def test_drops_irrelevant_items_and_keeps_relevant(self):
        store = _CaptureStore()
        items = [
            self._item("SICO (Sigma Energy Compressindo) ekspansi pabrik"),
            self._item("Mengapa saham Sigma Lithium turun hari ini?"),
            self._item("Saham SigmaRoc melonjak 12%"),
        ]
        n = s._filter_and_insert(store, self._cfg(), items, "SICO", "Sigma Energy Compressindo")
        assert n == 1
        assert len(store.inserted) == 1
        assert "SICO (Sigma" in store.inserted[0]["title"]

    def test_gate_is_skipped_for_macro_news(self):
        """ticker=None (macro) has nothing to attribute, so nothing is dropped."""
        store = _CaptureStore()
        items = [self._item("BI naikkan suku bunga"), self._item("IHSG melemah")]
        n = s._filter_and_insert(store, self._cfg(), items, None, None)
        assert n == 2

    def test_scrape_passes_company_names_to_the_gate(self, monkeypatch):
        cfg = {"api_key": "k", "url": "https://x", "count": 5, "country": "id",
               "lang": "", "sources": [], "macro_queries": []}
        monkeypatch.setattr(s, "get_config", lambda: cfg)
        store = _CaptureStore({"SICO": "Sigma Energy Compressindo"})
        monkeypatch.setattr(s, "ScraperDatabase", lambda: store)
        monkeypatch.setattr(
            s, "fetch_brave_news",
            lambda c, q: [
                {"title": "SICO raih kontrak", "url": "https://x/1"},
                {"title": "SigmaRoc melonjak", "url": "https://x/2"},
            ],
        )
        n = s.scrape_brave_news(tickers=["SICO"], delay=0)
        assert n == 1
        assert [r["title"] for r in store.inserted] == ["SICO raih kontrak"]


class TestMacro:
    def test_normalize_item_none_ticker_for_macro(self):
        """Macro/general news is stored without a ticker (NULL)."""
        rec = s.normalize_item({"title": "BI naikkan suku bunga", "url": "https://x/1", "page_age": "2026-09-05T00:00:00"}, None)
        assert rec is not None
        assert rec["ticker"] is None

    def test_macro_uses_config_queries_and_stores_null_ticker(self, monkeypatch):
        """--macro uses BRAVE_MACRO_QUERIES and persists each result with ticker=None."""
        cfg = {
            "api_key": "k", "url": "https://x", "count": 5, "country": "", "lang": "",
            "sources": [], "macro_queries": ["ekonomi indonesia", "ihsg"],
        }
        monkeypatch.setattr(s, "get_config", lambda: cfg)
        seen = []
        monkeypatch.setattr(s, "fetch_brave_news", lambda c, q: seen.append(q) or [])
        monkeypatch.setattr(
            s, "_filter_and_insert", lambda store, c, items, ticker: seen.append(ticker) or 0
        )
        monkeypatch.setattr(s, "ScraperDatabase", lambda: _FakeStore())
        result = s.scrape_brave_macro(limit=5, delay=0)
        assert result == 0
        assert "ekonomi indonesia" in seen
        assert "ihsg" in seen
        # General news is stored without a ticker (None) — not "NONE".
        assert seen.count(None) >= 2

    def test_macro_returns_zero_without_queries(self, monkeypatch):
        """No configured queries -> abort with a helpful message (no API hit)."""
        cfg = {"api_key": "k", "url": "https://x", "count": 5, "country": "", "lang": "", "sources": [], "macro_queries": []}
        monkeypatch.setattr(s, "get_config", lambda: cfg)
        hit = []
        monkeypatch.setattr(s, "fetch_brave_news", lambda c, q: hit.append(q) or [])
        result = s.scrape_brave_macro(delay=0)
        assert result == 0
        assert hit == []
