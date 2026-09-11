"""
Tests for API module (Phase 15).

Tests cover:
- API endpoint functionality
- Request/response validation
- Error handling
"""

from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.main import app

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# =============================================================================
# TESTS FOR HEALTH ENDPOINT
# =============================================================================

class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "phases_completed" in data


# =============================================================================
# TESTS FOR STOCK ENDPOINTS
# =============================================================================

class TestStockEndpoints:
    """Tests for stock-related endpoints."""

    def test_get_stock_price(self, client):
        """Test stock price endpoint."""
        response = client.get("/stocks/BBCA/price")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "BBCA"

    def test_get_fundamentals(self, client):
        """Test fundamentals endpoint."""
        response = client.get("/stocks/BBCA/fundamentals")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "BBCA"

    def test_get_technical(self, client):
        """Test technical analysis endpoint."""
        response = client.get("/stocks/BBCA/technical")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "BBCA"

    def test_get_valuation(self, client):
        """Test valuation endpoint."""
        response = client.get("/stocks/BBCA/valuation")
        assert response.status_code == 200

    def test_get_historical(self, client):
        """Test historical analysis endpoint."""
        response = client.get("/stocks/BBCA/historical")
        assert response.status_code == 200


# =============================================================================
# TESTS FOR DASHBOARD & STOCK-PAGE ENDPOINTS (Phase 25)
# =============================================================================

class TestDashboardEndpoints:
    """Tests for dashboard list / price-history / profile endpoints."""

    def test_list_stocks(self, client, monkeypatch):
        """Test GET /stocks returns list + change."""
        from unittest.mock import MagicMock
        loader = MagicMock()
        loader.list_stocks.return_value = [
            {"ticker": "BBCA", "name": "Bank Central Asia", "close": 100.0, "change": 2.0, "change_pct": 2.04}
        ]
        # The handler imports get_data_loader lazily from ai.data_loader_pg.
        monkeypatch.setattr("ai.data_loader_pg.get_data_loader", MagicMock(return_value=loader))
        response = client.get("/stocks")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["stocks"][0]["ticker"] == "BBCA"
        assert data["stocks"][0]["change_pct"] == 2.04

    def test_stocks_pagination(self, client, monkeypatch):
        """Test GET /stocks?page&limit slices the list and reports total/pages."""
        from unittest.mock import MagicMock
        loader = MagicMock()
        loader.list_stocks.return_value = [
            {"ticker": f"T{i}", "name": f"Name {i}", "close": float(i)}
            for i in range(1, 6)
        ]
        monkeypatch.setattr("ai.data_loader_pg.get_data_loader", MagicMock(return_value=loader))
        response = client.get("/stocks?page=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert data["pages"] == 3
        assert data["page"] == 2
        assert data["limit"] == 2
        assert data["count"] == 2
        # page 2 of 2-per-page -> T3, T4
        assert [s["ticker"] for s in data["stocks"]] == ["T3", "T4"]

    def test_stocks_pagination_default_full(self, client, monkeypatch):
        """Without limit, GET /stocks returns the full list (backward compat)."""
        from unittest.mock import MagicMock
        loader = MagicMock()
        loader.list_stocks.return_value = [
            {"ticker": f"T{i}", "name": f"Name {i}", "close": float(i)}
            for i in range(1, 6)
        ]
        monkeypatch.setattr("ai.data_loader_pg.get_data_loader", MagicMock(return_value=loader))
        response = client.get("/stocks")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert data["count"] == 5
        assert data["pages"] == 1

    def test_stocks_filter_and_sort(self, client, monkeypatch):
        """GET /stocks supports q/sector filter and sort/dir."""
        from unittest.mock import MagicMock
        loader = MagicMock()
        loader.list_stocks.return_value = [
            {"ticker": "BBCA", "name": "Bank Central Asia", "sector": "Keuangan", "close": 100.0, "change_pct": 2.0},
            {"ticker": "ASII", "name": "Astra", "sector": "Industri", "close": 50.0, "change_pct": -1.0},
            {"ticker": "BBRI", "name": "Bank Rakyat", "sector": "Keuangan", "close": 80.0, "change_pct": 3.0},
        ]
        monkeypatch.setattr("ai.data_loader_pg.get_data_loader", MagicMock(return_value=loader))
        # sector filter
        r = client.get("/stocks?sector=Keuangan")
        assert [s["ticker"] for s in r.json()["stocks"]] == ["BBCA", "BBRI"]
        # q filter (ticker substring)
        r = client.get("/stocks?q=BBCA")
        assert [s["ticker"] for s in r.json()["stocks"]] == ["BBCA"]
        # sort by close ascending
        r = client.get("/stocks?sort=close&dir=asc")
        assert [s["ticker"] for s in r.json()["stocks"]] == ["ASII", "BBRI", "BBCA"]

    def test_stocks_meta(self, client, monkeypatch):
        """GET /stocks/meta returns aggregate stats + sectors."""
        from unittest.mock import MagicMock
        loader = MagicMock()
        loader.list_stocks.return_value = [
            {"ticker": "BBCA", "sector": "Keuangan", "close": 100.0, "change": 2.0},
            {"ticker": "ASII", "sector": "Industri", "close": 50.0, "change": -1.0},
            {"ticker": "BBRI", "sector": "Keuangan", "close": None, "change": None},
        ]
        monkeypatch.setattr("ai.data_loader_pg.get_data_loader", MagicMock(return_value=loader))
        response = client.get("/stocks/meta")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["priced"] == 2
        assert data["advancers"] == 1
        assert data["decliners"] == 1
        assert data["sectors"] == ["Industri", "Keuangan"]

    def test_stocks_quote_batch(self, client, monkeypatch):
        """GET /stocks/quote returns only the requested tickers."""
        from unittest.mock import MagicMock
        loader = MagicMock()
        loader.list_stocks.return_value = [
            {"ticker": "BBCA", "name": "Bank", "sector": "Keuangan", "close": 100.0, "change_pct": 2.0},
            {"ticker": "ASII", "name": "Astra", "sector": "Industri", "close": 50.0, "change_pct": -1.0},
        ]
        monkeypatch.setattr("ai.data_loader_pg.get_data_loader", MagicMock(return_value=loader))
        response = client.get("/stocks/quote?tickers=BBCA")
        assert response.status_code == 200
        quotes = response.json()["quotes"]
        assert set(quotes.keys()) == {"BBCA"}
        assert quotes["BBCA"]["close"] == 100.0

    def test_stocks_index(self, client, monkeypatch):
        """GET /stocks/index returns lightweight rows for search."""
        from unittest.mock import MagicMock
        loader = MagicMock()
        loader.list_stocks.return_value = [
            {"ticker": "BBCA", "name": "Bank Central Asia", "sector": "Keuangan", "close": 100.0},
            {"ticker": "BBRI", "name": "Bank Rakyat", "sector": "Keuangan", "close": 80.0},
        ]
        monkeypatch.setattr("ai.data_loader_pg.get_data_loader", MagicMock(return_value=loader))
        response = client.get("/stocks/index?q=Bank")
        assert response.status_code == 200
        rows = response.json()["rows"]
        assert [r["ticker"] for r in rows] == ["BBCA", "BBRI"]
        assert all("close" not in r for r in rows)

    def test_price_history(self, client, monkeypatch):
        """Test GET /stocks/{ticker}/prices returns ordered series."""
        from unittest.mock import MagicMock
        loader = MagicMock()
        loader.get_price_history.return_value = [{"date": "2026-08-27", "close": 100.0}, {"date": "2026-08-28", "close": 102.0}]
        monkeypatch.setattr("ai.data_loader_pg.get_data_loader", MagicMock(return_value=loader))
        response = client.get("/stocks/BBCA/prices")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "BBCA"
        assert len(data["prices"]) == 2

    def test_stock_profile(self, client, monkeypatch):
        """Test GET /stocks/{ticker} returns profile/quote/metrics keys."""
        from unittest.mock import MagicMock
        loader = MagicMock()
        loader.get_company_info.return_value = {"ticker": "BBCA", "name": "Bank Central Asia"}
        loader.get_stock_price.return_value = {"price": 100.0, "volume": 1000}
        loader.get_financial_ratios.return_value = {"roe": 20.0}
        monkeypatch.setattr("ai.data_loader_pg.get_data_loader", MagicMock(return_value=loader))
        response = client.get("/stocks/BBCA")
        assert response.status_code == 200
        data = response.json()
        assert data["profile"]["name"] == "Bank Central Asia"

    def test_stock_financial_history(self, client, monkeypatch):
        """Test GET /stocks/{ticker}/financials/history returns ordered series."""
        from unittest.mock import MagicMock
        loader = MagicMock()
        loader.get_financial_ratio_history.return_value = [
            {"period_end": "2024-12-31", "revenue": 100000.0, "net_income": 20000.0, "net_margin": 20.0},
            {"period_end": "2025-12-31", "revenue": 120000.0, "net_income": 24000.0, "net_margin": 20.0},
        ]
        monkeypatch.setattr("ai.data_loader_pg.get_data_loader", MagicMock(return_value=loader))
        response = client.get("/stocks/BBCA/financials/history")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "BBCA"
        assert len(data["series"]) == 2
        assert data["series"][0]["revenue"] == 100000.0
        assert data["series"][1]["net_margin"] == 20.0

    def test_screen_analysis_returns_llm_and_results(self, client, monkeypatch):
        """Test POST /ai/screen-analysis returns deterministic results + LLM field."""
        from unittest.mock import MagicMock
        loader = MagicMock()
        loader.list_stock_metrics.return_value = {
            "BBCA": {"roe": 20.0, "net_margin": 30.0, "pe_ratio": 15.0},
            "BBRI": {"roe": 18.0, "net_margin": 25.0, "pe_ratio": 12.0},
        }
        monkeypatch.setattr("ai.data_loader_pg.get_data_loader", MagicMock(return_value=loader))
        screen_result = {
            "results": [
                {"ticker": "BBCA", "passed": True, "pass_rate": 100.0, "score": 8.0,
                 "filter_results": {"roe": {"filter": "roe", "value": 20.0, "passed": True}}},
                {"ticker": "BBRI", "passed": False, "pass_rate": 50.0, "score": 4.0,
                 "filter_results": {"roe": {"filter": "roe", "value": 18.0, "passed": False}}},
            ],
            "count": 2,
        }
        monkeypatch.setattr("api.main.run_screening", MagicMock(return_value=screen_result))
        # Isolate the LLM: the endpoint's LLMClient would otherwise make a real
        # network call (OPENAI_API_KEY is set in .env), making the test slow.
        llm_client = MagicMock()
        llm_client.is_available = True
        llm_client.analyze_with_prompt.return_value = {"content": "Mock AI interpretation"}
        monkeypatch.setattr("ai.llm.LLMClient", MagicMock(return_value=llm_client))
        # Isolate persistence: avoid a real DB write during the test.
        fake_store = MagicMock()
        fake_store.save_screen_analysis.return_value = 99
        fake_store.__enter__.return_value = fake_store
        fake_store.__exit__.return_value = False
        monkeypatch.setattr("database.scraper_store.ScraperDatabase", MagicMock(return_value=fake_store))
        response = client.post("/ai/screen-analysis", json={"screen_type": "growth", "top_n": 10})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["passed"] == 1
        assert data["results"][0]["ticker"] == "BBCA"
        assert data["llm_analysis"] == "Mock AI interpretation"
        assert data["analysis_id"] == 99

    def test_screen_analysis_history(self, client, monkeypatch):
        """Test GET /ai/screen-analysis/history returns saved analyses."""
        from unittest.mock import MagicMock
        fake_store = MagicMock()
        fake_store.get_screen_analyses.return_value = [
            {"id": 1, "screen_type": "growth", "created_at": "2026-09-08T10:00:00",
             "llm_analysis": "**Summary**", "tickers": ["BBCA"], "results": [], "filters": []},
        ]
        fake_store.__enter__.return_value = fake_store
        fake_store.__exit__.return_value = False
        monkeypatch.setattr("database.scraper_store.ScraperDatabase", MagicMock(return_value=fake_store))
        response = client.get("/ai/screen-analysis/history?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["analyses"][0]["screen_type"] == "growth"
        assert "Summary" in data["analyses"][0]["llm_analysis"]

    def test_research_history(self, client, monkeypatch):
        """Test GET /stocks/{ticker}/research-history returns saved reports."""
        from unittest.mock import MagicMock
        reports = [
            {"ticker": "BBCA", "saved_at": "2026-09-01T10:00:00", "confidence_score": 0.7,
             "overall_verdict": "Buy", "sections": {"executive_summary": "Solid bank."}},
        ]
        monkeypatch.setattr("ai.memory.get_research_history", MagicMock(return_value=reports))
        response = client.get("/stocks/BBCA/research-history")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["reports"][0]["ticker"] == "BBCA"

    def test_thesis_comparison(self, client, monkeypatch):
        """Test GET /stocks/{ticker}/thesis-comparison returns comparison result."""
        from unittest.mock import MagicMock
        comparison = {"reports_analyzed": 2, "comparisons": [{"confidence_change": {"change": 0.1}}]}
        monkeypatch.setattr("ai.memory.compare_research_theses", MagicMock(return_value=comparison))
        response = client.get("/stocks/BBCA/thesis-comparison")
        assert response.status_code == 200
        data = response.json()
        assert data["reports_analyzed"] == 2
        assert len(data["comparisons"]) == 1

    def test_ai_fundamental(self, client, monkeypatch):
        """Test POST /ai/fundamental returns deterministic ratios + signal."""
        from unittest.mock import MagicMock
        loader = MagicMock()
        loader.get_financial_ratios_merged.return_value = {
            "ticker": "BBRI", "pe_ratio": 10.11, "pb_ratio": 1.88,
            "roe": 18.57, "debt_to_equity": 4.95, "net_margin": 30.32,
        }
        monkeypatch.setattr("ai.data_loader_pg.get_data_loader", MagicMock(return_value=loader))
        response = client.post("/ai/fundamental", json={"ticker": "BBRI"})
        assert response.status_code == 200
        data = response.json()
        assert data["key_ratios"]["pe_ratio"] == 10.11
        assert data["score"] > 0
        assert data["signal"] in ("BULLISH", "NEUTRAL", "BEARISH")

    def test_research_candidates_rank_validity(self, client, monkeypatch):
        """Test GET /research/candidates?rank=validity passes rank + validator fields."""
        from unittest.mock import MagicMock

        loader = MagicMock()
        loader.get_research_candidates.return_value = [
            {
                "candidate_date": "2026-09-08",
                "sector": "Keuangan",
                "ticker": "BBCA",
                "direction": "positive",
                "confidence": 0.6,
                "net_strength": 2.5,
                "reason": "Macro tailwind",
                "status": "pending",
                "validator_score": 82.0,
                "validator_tier": "HIGH",
            }
        ]
        monkeypatch.setattr("ai.data_loader_pg.get_data_loader", MagicMock(return_value=loader))
        response = client.get("/research/candidates?rank=validity")
        assert response.status_code == 200
        data = response.json()
        assert data["rank"] == "validity"
        assert len(data["candidates"]) == 1
        call_kwargs = loader.get_research_candidates.call_args.kwargs
        assert call_kwargs.get("rank") == "validity"
        cand = data["candidates"][0]
        assert cand["validator_score"] == 82.0
        assert cand["validator_tier"] == "HIGH"

    def test_research_candidates_filter_bullish_validity(self, client, monkeypatch):
        """Test GET /research/candidates?filter=bullish_validity passes filter + min_validity."""
        from unittest.mock import MagicMock

        loader = MagicMock()
        loader.get_research_candidates.return_value = [
            {
                "candidate_date": "2026-09-08",
                "sector": "Energi",
                "ticker": "ADRO",
                "direction": "positive",
                "confidence": 0.7,
                "net_strength": 3.0,
                "reason": "Energy rally",
                "status": "pending",
                "validator_score": 76.0,
                "validator_tier": "HIGH",
            }
        ]
        monkeypatch.setattr("ai.data_loader_pg.get_data_loader", MagicMock(return_value=loader))
        response = client.get("/research/candidates?filter=bullish_validity&min_validity=70")
        assert response.status_code == 200
        data = response.json()
        assert data["filter"] == "bullish_validity"
        assert data["min_validity"] == 70.0
        call_kwargs = loader.get_research_candidates.call_args.kwargs
        assert call_kwargs.get("filter") == "bullish_validity"
        assert call_kwargs.get("min_validity") == 70.0
        assert data["candidates"][0]["validator_score"] == 76.0

    def test_web_interface_serves_html(self, client):
        """Test GET / serves the dashboard HTML."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "IDX-BEI Dashboard" in response.text

    def test_stock_page_serves_html(self, client):
        """Test GET /stock/{ticker} serves the SPA for client-side routing."""
        response = client.get("/stock/BBCA")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "IDX-BEI Dashboard" in response.text


class TestNewsEndpoints:
    """Tests for news & events endpoints (Phase 8 / Iterasi 4 backend)."""

    def test_stock_news(self, client, monkeypatch):
        from unittest.mock import MagicMock

        loader = MagicMock()
        loader.get_news.return_value = [
            {"ticker": "BBCA", "title": "BBCA Dividend", "source": "IDX", "url": "http://x"}
        ]
        monkeypatch.setattr("ai.data_loader_pg.get_data_loader", MagicMock(return_value=loader))
        response = client.get("/stocks/BBCA/news")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "BBCA"
        assert data["count"] == 1
        assert data["news"][0]["ticker"] == "BBCA"

    def test_stock_events(self, client, monkeypatch):
        from unittest.mock import MagicMock

        loader = MagicMock()
        loader.get_news.return_value = [
            {"ticker": "BBCA", "title": "BBCA Umumkan Dividen Interim", "content": "", "source": "IDX", "url": "http://x"}
        ]
        monkeypatch.setattr("ai.data_loader_pg.get_data_loader", MagicMock(return_value=loader))
        monkeypatch.setattr("events.classif_news_records", MagicMock(return_value=[{"event_type": "dividend", "tickers": ["BBCA"]}]))
        response = client.get("/stocks/BBCA/events")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["events"][0]["event_type"] == "dividend"

    def test_all_news(self, client, monkeypatch):
        from unittest.mock import MagicMock

        loader = MagicMock()
        loader.get_news.return_value = [{"title": "N1"}, {"title": "N2"}]
        monkeypatch.setattr("ai.data_loader_pg.get_data_loader", MagicMock(return_value=loader))
        response = client.get("/news?limit=5")
        assert response.status_code == 200
        assert response.json()["count"] == 2


class TestScreenerCompareEndpoints:
    """Tests for screening and comparison endpoints (Phase 25 Iterasi 3)."""

    def test_screen_custom_filters(self, client, monkeypatch):
        """Test POST /screen builds stocks from DB and runs screening."""
        from unittest.mock import MagicMock

        loader = MagicMock()
        loader.list_stock_metrics.return_value = {
            "BBCA": {"roe": 20.0, "pe_ratio": 15.0},
            "BBRI": {"roe": 18.0, "pe_ratio": 10.0},
        }
        monkeypatch.setattr("ai.data_loader_pg.get_data_loader", MagicMock(return_value=loader))

        mock_result = {
            "results": [{"ticker": "BBCA", "passed": True, "score": 2.0, "pass_rate": 1.0, "filter_results": {}}],
            "count": 1,
            "stocks_passed": 1,
            "total_screened": 2,
        }
        mock_screen = MagicMock(return_value=mock_result)
        monkeypatch.setattr("api.main.run_screening", mock_screen)

        response = client.post(
            "/screen",
            json={"filters": [{"metric": "roe", "operator": ">", "value": 15.0}]},
        )
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["stocks_passed"] == 1
        # Ensure run_screening got the metrics map (not an empty dict)
        _, kwargs = mock_screen.call_args
        assert kwargs.get("stocks") == {"BBCA": {"roe": 20.0, "pe_ratio": 15.0}, "BBRI": {"roe": 18.0, "pe_ratio": 10.0}}

    def test_screen_predefined_type(self, client, monkeypatch):
        """Test POST /screen with a predefined screen type."""
        from unittest.mock import MagicMock

        loader = MagicMock()
        loader.list_stock_metrics.return_value = {"BBCA": {"roe": 20.0}}
        monkeypatch.setattr("ai.data_loader_pg.get_data_loader", MagicMock(return_value=loader))

        mock_result = {"results": [], "count": 0, "stocks_passed": 0, "total_screened": 1}
        monkeypatch.setattr("api.main.run_screening", MagicMock(return_value=mock_result))
        response = client.post("/screen", json={"screen_type": "buffett"})
        assert response.status_code == 200
        assert response.json()["stocks_passed"] == 0

    def test_compare_stocks(self, client, monkeypatch):
        """Test GET /compare returns side-by-side metrics."""
        from unittest.mock import MagicMock

        loader = MagicMock()
        loader.list_stock_metrics.return_value = {
            "BBCA": {"roe": 20.0, "pe_ratio": 15.0},
            "BBRI": {"roe": 18.0, "pe_ratio": 10.0},
        }
        loader.get_company_info.side_effect = lambda t: {"ticker": t, "name": t + " Name", "sector": "Banking"}
        loader.get_stock_price.side_effect = lambda t: {"price": 100.0, "as_of": "2026-08-28"}
        monkeypatch.setattr("ai.data_loader_pg.get_data_loader", MagicMock(return_value=loader))

        response = client.get("/compare?tickers=BBCA,BBRI")
        assert response.status_code == 200
        data = response.json()
        assert data["tickers"] == ["BBCA", "BBRI"]
        assert len(data["stocks"]) == 2
        assert data["stocks"][0]["metrics"]["roe"] == 20.0


class TestFavoritesEndpoints:
    """Tests for favorites routes with a mocked store."""

    def test_get_favorites(self, client, monkeypatch):
        from unittest.mock import MagicMock
        store = MagicMock()
        store.get_favorites.return_value = ["BBCA", "BBRI"]
        class FakeCtx:
            def __enter__(self): return store
            def __exit__(self, *a): return False
        monkeypatch.setattr("api.main.ScraperDatabase", lambda: FakeCtx())
        response = client.get("/favorites")
        assert response.status_code == 200
        assert response.json()["tickers"] == ["BBCA", "BBRI"]

    def test_add_favorite(self, client, monkeypatch):
        from unittest.mock import MagicMock
        store = MagicMock()
        store.add_favorite.return_value = True
        class FakeCtx:
            def __enter__(self): return store
            def __exit__(self, *a): return False
        monkeypatch.setattr("api.main.ScraperDatabase", lambda: FakeCtx())
        response = client.post("/favorites/BBCA")
        assert response.status_code == 200
        assert response.json()["added"] is True

    def test_remove_favorite(self, client, monkeypatch):
        from unittest.mock import MagicMock
        store = MagicMock()
        store.remove_favorite.return_value = True
        class FakeCtx:
            def __enter__(self): return store
            def __exit__(self, *a): return False
        monkeypatch.setattr("api.main.ScraperDatabase", lambda: FakeCtx())
        response = client.delete("/favorites/BBCA")
        assert response.status_code == 200
        assert response.json()["removed"] is True

    def test_set_price_alert(self, client, monkeypatch):
        from unittest.mock import MagicMock
        store = MagicMock()
        store.set_price_alert.return_value = True
        class FakeCtx:
            def __enter__(self): return store
            def __exit__(self, *a): return False
        monkeypatch.setattr("api.main.ScraperDatabase", lambda: FakeCtx())
        response = client.post("/favorites/BBCA/alert", json={"alert_price": 8000, "direction": "above"})
        assert response.status_code == 200
        assert response.json()["set"] is True
        assert response.json()["alert_price"] == 8000

    def test_remove_price_alert(self, client, monkeypatch):
        from unittest.mock import MagicMock
        store = MagicMock()
        store.remove_price_alert.return_value = True
        class FakeCtx:
            def __enter__(self): return store
            def __exit__(self, *a): return False
        monkeypatch.setattr("api.main.ScraperDatabase", lambda: FakeCtx())
        response = client.delete("/favorites/BBCA/alert")
        assert response.status_code == 200
        assert response.json()["removed"] is True

    def test_get_triggered_alerts(self, client, monkeypatch):
        from unittest.mock import MagicMock
        store = MagicMock()
        store.get_triggered_alerts.return_value = [{"ticker": "BBCA", "alert_price": 7000.0, "triggered": True}]
        class FakeCtx:
            def __enter__(self): return store
            def __exit__(self, *a): return False
        monkeypatch.setattr("api.main.ScraperDatabase", lambda: FakeCtx())
        response = client.get("/favorites/alerts")
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["alerts"][0]["ticker"] == "BBCA"

    def test_favorites_details(self, client, monkeypatch):
        from unittest.mock import MagicMock
        store = MagicMock()
        store.get_favorites_details.return_value = [{"ticker": "BBCA", "alert_price": 8000.0, "current_price": 6700.0}]
        class FakeCtx:
            def __enter__(self): return store
            def __exit__(self, *a): return False
        monkeypatch.setattr("api.main.ScraperDatabase", lambda: FakeCtx())
        response = client.get("/favorites/details")
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["favorites"][0]["alert_price"] == 8000.0


# =============================================================================
# TESTS FOR AI ENDPOINTS
# =============================================================================

class TestAIEndpoints:
    """Tests for AI research endpoints."""

    def test_ai_analyze_stock(self, client, monkeypatch):
        """Test AI stock analysis endpoint."""
        from datetime import datetime
        from unittest.mock import MagicMock, patch

        from ai.researcher import ResearchReport

        # The endpoint now stamps the validator score onto research_candidates,
        # so isolate the DB write (otherwise it opens a real connection).
        fake_store = MagicMock()
        fake_store.update_candidate_validity.return_value = 0
        fake_store.__enter__.return_value = fake_store
        fake_store.__exit__.return_value = False
        monkeypatch.setattr("api.main.ScraperDatabase", MagicMock(return_value=fake_store))

        # Create a mock report with all required attributes
        mock_report = ResearchReport(
            ticker="BBCA",
            question="Is BBCA a good investment?",
            executive_summary="Mock summary for testing",
            timestamp=datetime.now(),
        )

        # Patch the analyze_stock function
        fetch_mock = MagicMock()
        monkeypatch.setattr("api.main._fetch_fresh_ticker_news", fetch_mock)
        with patch('api.main.analyze_stock', return_value=mock_report):
            response = client.post(
                "/ai/analyze",
                json={"ticker": "BBCA", "question": "Is BBCA a good investment?"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == "BBCA"
            fetch_mock.assert_called_once()

    def test_ai_compare_stocks(self, client):
        """Test AI stock comparison endpoint."""
        from datetime import datetime
        from unittest.mock import patch

        from ai.researcher import ResearchReport

        # Create a mock report
        mock_report = ResearchReport(
            ticker="BBCA",
            question="Compare these banks",
            executive_summary="Mock comparison for testing",
            timestamp=datetime.now(),
        )

        # Patch the compare_stocks function
        with patch('api.main.compare_stocks', return_value=mock_report):
            response = client.post(
                "/ai/compare",
                json={"tickers": ["BBCA", "BBRI"], "question": "Compare these banks"}
            )
            assert response.status_code == 200


# =============================================================================
# TESTS FOR DOCUMENT ENDPOINTS
# =============================================================================

class TestDocumentEndpoints:
    """Tests for document search endpoints."""

    def test_add_document(self, client):
        """Test adding a document."""
        response = client.post(
            "/documents/add",
            params={
                "doc_id": "test_doc_1",
                "content": "Test document content about banking.",
                "ticker": "BBCA",
                "doc_type": "news",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_search_documents(self, client):
        """Test document search."""
        response = client.post(
            "/documents/search",
            json={"query": "banking growth", "top_k": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "count" in data


# =============================================================================
# TESTS FOR ERROR HANDLING
# =============================================================================

class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_ticker(self, client):
        """Test handling of invalid ticker."""
        response = client.get("/stocks/INVALID/price")
        # Should return 200 with notes about missing data
        assert response.status_code == 200


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self, client, monkeypatch):
        """Test complete workflow from analysis to report."""
        from datetime import datetime
        from unittest.mock import MagicMock

        # Create a mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ticker": "BBCA",
            "question": "How is BBCA performing?",
            "generated_at": datetime.now().isoformat(),
            "confidence_score": 0.5,
            "overall_verdict": "",
            "claim_summary": {"FACT": 0, "INTERPRETATION": 0, "ASSUMPTION": 0, "SPECULATION": 0},
            "sections": {
                "executive_summary": "Mock summary",
                "business_quality": "",
                "growth_analysis": "",
                "profitability": "",
                "financial_health": "",
                "valuation": "",
                "technical_position": "",
                "recent_events": "",
                "risks": "",
                "bull_case": "",
                "base_case": "",
                "bear_case": "",
                "conclusion": "",
            }
        }

        # Mock the entire endpoint to avoid any processing
        monkeypatch.setattr('api.main.ai_analyze_stock', MagicMock(return_value=mock_response))

        # Add a document
        response = client.post(
            "/documents/add",
            params={
                "doc_id": "workflow_test",
                "content": "BBCA reported strong Q4 results with 15% revenue growth.",
                "ticker": "BBCA",
                "doc_type": "earnings",
            }
        )
        assert response.status_code == 200

        # Search for it
        response = client.post(
            "/documents/search",
            json={"query": "BBCA revenue growth", "ticker": "BBCA"}
        )
        assert response.status_code == 200

        # Analyze stock
        response = client.post(
            "/ai/analyze",
            json={"ticker": "BBCA", "question": "How is BBCA performing?"}
        )
        assert response.status_code == 200


class TestAiStreamSse:
    """The AI chat endpoint must emit structured SSE events (status -> chunk -> done)."""

    def test_stream_emits_status_and_chunks(self, client, monkeypatch):
        from types import SimpleNamespace
        from unittest.mock import MagicMock

        def make_chunks():
            for tok in ["Halo", " ", "dunia"]:
                yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=tok))])

        fake = MagicMock()
        fake.model = "gpt-4o"
        fake.client.chat.completions.create.return_value = make_chunks()
        monkeypatch.setattr("api.main.AIResearcher", MagicMock(return_value=fake))
        monkeypatch.setattr("api.main._fetch_fresh_ticker_news", MagicMock())

        response = client.post("/ai/analyze-stream", json={"ticker": "BBCA", "question": "prospek?"})
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        text = response.text
        assert "event: status" in text
        assert "event: chunk" in text
        assert "Halo" in text and "dunia" in text
        assert "event: done" in text

    def test_stream_emits_error_when_no_llm(self, client, monkeypatch):
        from unittest.mock import MagicMock
        fake = MagicMock()
        fake.client = None
        fake.model = "gpt-4o"
        monkeypatch.setattr("api.main.AIResearcher", MagicMock(return_value=fake))
        response = client.post("/ai/analyze-stream", json={"ticker": "BBCA", "question": "x"})
        assert response.status_code == 200
        assert "event: error" in response.text


class TestResearchGenerateGuard:
    """POST /stocks/{ticker}/research/analyze must skip when a recent report exists."""

    def test_skips_when_recent_report(self, client, monkeypatch):
        from datetime import datetime, timedelta
        from unittest.mock import MagicMock
        recent = {"ticker": "BBCA", "saved_at": datetime.now().isoformat(),
                  "confidence_score": 0.7, "overall_verdict": "Buy"}
        memory = MagicMock()
        memory.get_latest_report.return_value = recent
        monkeypatch.setattr("ai.memory.ResearchMemory", MagicMock(return_value=memory))
        save_mock = MagicMock()
        monkeypatch.setattr("ai.memory.save_research_report", save_mock)
        analyze_mock = MagicMock()
        monkeypatch.setattr("ai.researcher.analyze_stock", analyze_mock)

        response = client.post("/stocks/BBCA/research/analyze?min_hours=24")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"
        assert data["reason"] == "recent_analysis"
        # Should NOT have regenerated or saved.
        analyze_mock.assert_not_called()
        save_mock.assert_not_called()

    def test_generates_and_fetches_fresh_news_when_no_recent_report(self, client, monkeypatch):
        """When no recent report exists, on-demand per-ticker news is fetched first."""
        from datetime import datetime
        from unittest.mock import MagicMock

        from ai.researcher import ResearchReport

        memory = MagicMock()
        memory.get_latest_report.return_value = None
        monkeypatch.setattr("ai.memory.ResearchMemory", MagicMock(return_value=memory))
        save_mock = MagicMock()
        monkeypatch.setattr("ai.memory.save_research_report", save_mock)
        fetch_mock = MagicMock()
        monkeypatch.setattr("api.main._fetch_fresh_ticker_news", fetch_mock)

        mock_report = ResearchReport(
            ticker="BBCA",
            question="Is BBCA a good investment?",
            executive_summary="Mock summary",
            timestamp=datetime.now(),
        )
        # generate_research imports analyze_stock from ai.researcher *inside* the
        # function, so the patch target must be ai.researcher (not api.main).
        monkeypatch.setattr("ai.researcher.analyze_stock", MagicMock(return_value=mock_report))
        # Avoid the validator / DB stamping branches.
        monkeypatch.setattr("api.main._attach_validator", MagicMock(side_effect=lambda d: d))
        monkeypatch.setattr("api.main._stamp_candidate_validity", MagicMock())

        response = client.post("/stocks/BBCA/research/analyze?min_hours=24")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "generated"
        assert data["report"]["ticker"] == "BBCA"
        # On-demand news must be fetched before generating the analysis.
        fetch_mock.assert_called_once()
        save_mock.assert_called_once()


class TestOnDemandNewsFetch:
    """On-demand ticker news is only scraped when no recent news exists."""

    def test_skips_scrape_when_recent_news_exists(self, monkeypatch):
        from datetime import datetime
        from unittest.mock import MagicMock

        import api.main as m

        monkeypatch.setenv("BRAVE_API_KEY", "test")
        monkeypatch.setattr(
            "ai.tools.get_company_news",
            MagicMock(return_value={"news": [{"published_at": datetime.now().isoformat()}]}),
        )
        scrape = MagicMock()
        monkeypatch.setattr("scrape_brave_news.scrape_brave_news", scrape)

        m._fetch_fresh_ticker_news("BBCA")

        scrape.assert_not_called()

    def test_scrapes_when_no_recent_news(self, monkeypatch):
        from unittest.mock import MagicMock

        import api.main as m

        monkeypatch.setenv("BRAVE_API_KEY", "test")
        # No stored news at all -> must fetch.
        monkeypatch.setattr("ai.tools.get_company_news", MagicMock(return_value={"news": []}))
        scrape = MagicMock(return_value=2)
        monkeypatch.setattr("scrape_brave_news.scrape_brave_news", scrape)
        monkeypatch.setattr("ai.data_loader_pg.clear_cache", MagicMock())

        m._fetch_fresh_ticker_news("BBCA")

        scrape.assert_called_once()

    def test_scrapes_when_news_is_stale(self, monkeypatch):
        from unittest.mock import MagicMock

        import api.main as m

        monkeypatch.setenv("BRAVE_API_KEY", "test")
        monkeypatch.setattr(
            "ai.tools.get_company_news",
            MagicMock(return_value={"news": [{"published_at": "2020-01-01T00:00:00"}]}),
        )
        scrape = MagicMock(return_value=1)
        monkeypatch.setattr("scrape_brave_news.scrape_brave_news", scrape)
        monkeypatch.setattr("ai.data_loader_pg.clear_cache", MagicMock())

        m._fetch_fresh_ticker_news("BBCA")

        scrape.assert_called_once()

    def test_skips_when_no_brave_key(self, monkeypatch):
        from unittest.mock import MagicMock

        import api.main as m

        monkeypatch.delenv("BRAVE_API_KEY", raising=False)
        scrape = MagicMock()
        monkeypatch.setattr("scrape_brave_news.scrape_brave_news", scrape)

        m._fetch_fresh_ticker_news("BBCA")

        scrape.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
