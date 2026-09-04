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
        assert data["quote"]["price"] == 100.0
        assert data["metrics"]["roe"] == 20.0

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


# =============================================================================
# TESTS FOR AI ENDPOINTS
# =============================================================================

class TestAIEndpoints:
    """Tests for AI research endpoints."""

    def test_ai_analyze_stock(self, client):
        """Test AI stock analysis endpoint."""
        from datetime import datetime
        from unittest.mock import patch

        from ai.researcher import ResearchReport

        # Create a mock report with all required attributes
        mock_report = ResearchReport(
            ticker="BBCA",
            question="Is BBCA a good investment?",
            executive_summary="Mock summary for testing",
            timestamp=datetime.now(),
        )

        # Patch the analyze_stock function
        with patch('api.main.analyze_stock', return_value=mock_report):
            response = client.post(
                "/ai/analyze",
                json={"ticker": "BBCA", "question": "Is BBCA a good investment?"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == "BBCA"

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
