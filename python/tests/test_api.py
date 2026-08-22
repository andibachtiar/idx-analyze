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
# TESTS FOR AI ENDPOINTS
# =============================================================================

class TestAIEndpoints:
    """Tests for AI research endpoints."""

    def test_ai_analyze_stock(self, client):
        """Test AI stock analysis endpoint."""
        response = client.post(
            "/ai/analyze",
            json={"ticker": "BBCA", "question": "Is BBCA a good investment?"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "BBCA"

    def test_ai_compare_stocks(self, client):
        """Test AI stock comparison endpoint."""
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

    def test_full_workflow(self, client):
        """Test complete workflow from analysis to report."""
        # Add a document
        client.post(
            "/documents/add",
            params={
                "doc_id": "workflow_test",
                "content": "BBCA reported strong Q4 results with 15% revenue growth.",
                "ticker": "BBCA",
                "doc_type": "earnings",
            }
        )

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
