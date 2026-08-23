"""
Tests for Vector Search (Phase 14).

Tests cover:
- Document ingestion and storage
- Semantic search functionality
- Filtering by ticker and document type
- Persistence and loading
- Statistics tracking
"""

from __future__ import annotations

import os
import sys
import tempfile
from typing import Dict, List

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.vector import (
    DocumentProcessor,
    VectorStore,
    create_vector_store,
    search_documents,
)

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_storage():
    """Create a temporary storage path for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "vectors.json")


@pytest.fixture
def sample_documents():
    """Create sample documents for testing."""
    return [
        {
            "doc_id": "bbca_annual_2024",
            "content": "Bank Central Asia reported strong annual results with revenue growth of 12% and ROE of 25%.",
            "ticker": "BBCA",
            "doc_type": "annual_report",
            "metadata": {"year": 2024},
        },
        {
            "doc_id": "bbri_news_2024",
            "content": "Bank Rakyat Indonesia announces new digital banking initiative to expand customer base.",
            "ticker": "BBRI",
            "doc_type": "news",
            "metadata": {"date": "2024-01-15"},
        },
        {
            "doc_id": "bbca_earnings_2024",
            "content": "BBCA earnings call highlighted improved net interest margin and strong loan growth.",
            "ticker": "BBCA",
            "doc_type": "earnings",
            "metadata": {"quarter": "Q4"},
        },
        {
            "doc_id": "index_report",
            "content": "IDX Composite index reached new highs driven by banking sector strength.",
            "ticker": None,
            "doc_type": "market_report",
            "metadata": {},
        },
    ]


# =============================================================================
# TESTS FOR VECTOR STORE
# =============================================================================

class TestVectorStore:
    """Tests for VectorStore class."""

    def test_init_creates_empty_store(self):
        """Test initialization creates empty store."""
        store = VectorStore()
        assert len(store.documents) == 0
        assert len(store.embeddings) == 0

    def test_add_document(self, temp_storage):
        """Test adding a document."""
        store = VectorStore(storage_path=temp_storage)
        result = store.add_document(
            doc_id="test_1",
            content="This is a test document about banking.",
            ticker="BBCA",
            doc_type="news",
        )

        assert result is True
        assert "test_1" in store.documents
        assert store.documents["test_1"]["ticker"] == "BBCA"

    def test_add_multiple_documents(self, sample_documents):
        """Test adding multiple documents."""
        store = VectorStore()

        for doc in sample_documents:
            store.add_document(**doc)

        assert len(store.documents) == 4

    def test_remove_document(self, temp_storage):
        """Test removing a document."""
        store = VectorStore(storage_path=temp_storage)
        store.add_document("doc_1", "Content 1", ticker="BBCA")
        store.add_document("doc_2", "Content 2", ticker="BBRI")

        result = store.remove_document("doc_1")
        assert result is True
        assert len(store.documents) == 1
        assert "doc_1" not in store.documents

    def test_remove_nonexistent(self):
        """Test removing non-existent document."""
        store = VectorStore()
        result = store.remove_document("nonexistent")
        assert result is False

    def test_search_returns_results(self, temp_storage):
        """Test search returns relevant results."""
        store = VectorStore(storage_path=temp_storage)

        # Add documents
        store.add_document("doc_1", "Banking sector shows strong growth in Q4", ticker="BBCA")
        store.add_document("doc_2", "Technology stocks decline amid rate concerns", ticker="TLKM")
        store.add_document("doc_3", "Central bank raises interest rates", ticker=None)

        # Search
        results = store.search("banking growth", top_k=2)

        assert len(results) > 0
        assert results[0]["score"] > 0

    def test_search_with_ticker_filter(self, sample_documents):
        """Test search with ticker filter."""
        store = VectorStore()

        for doc in sample_documents:
            store.add_document(**doc)

        # Search only BBCA documents
        results = store.search("annual results", ticker="BBCA", top_k=2)

        for r in results:
            assert r["ticker"] == "BBCA"

    def test_search_with_doc_type_filter(self, sample_documents):
        """Test search with document type filter."""
        store = VectorStore()

        for doc in sample_documents:
            store.add_document(**doc)

        # Search only annual reports
        results = store.search("financial performance", doc_type="annual_report", top_k=2)

        for r in results:
            assert r["doc_type"] == "annual_report"

    def test_get_document(self, temp_storage):
        """Test getting a document by ID."""
        store = VectorStore(storage_path=temp_storage)
        store.add_document("doc_1", "Test content", ticker="BBCA")

        doc = store.get_document("doc_1")
        assert doc is not None
        assert doc["content"] == "Test content"
        assert doc["ticker"] == "BBCA"

    def test_get_nonexistent_document(self):
        """Test getting non-existent document."""
        store = VectorStore()
        doc = store.get_document("nonexistent")
        assert doc is None

    def test_get_documents_by_ticker(self, sample_documents):
        """Test getting documents by ticker."""
        store = VectorStore()

        for doc in sample_documents:
            store.add_document(**doc)

        bbcA_docs = store.get_documents_by_ticker("BBCA")
        assert len(bbcA_docs) == 2

        bbri_docs = store.get_documents_by_ticker("BBRI")
        assert len(bbri_docs) == 1

    def test_get_documents_by_type(self, sample_documents):
        """Test getting documents by type."""
        store = VectorStore()

        for doc in sample_documents:
            store.add_document(**doc)

        news_docs = store.get_documents_by_ticker("BBRI", doc_type="news")
        assert len(news_docs) == 1

    def test_statistics(self, sample_documents):
        """Test statistics tracking."""
        store = VectorStore()

        for doc in sample_documents:
            store.add_document(**doc)

        stats = store.get_statistics()

        assert stats["total_documents"] == 4
        assert stats["tickers"]["BBCA"] == 2
        assert stats["tickers"]["BBRI"] == 1
        assert "annual_report" in stats["document_types"]

    def test_persistence(self, temp_storage):
        """Test saving and loading from file."""
        # Create and populate store
        store1 = VectorStore(storage_path=temp_storage)
        store1.add_document("doc_1", "Content 1", ticker="BBCA")
        store1.add_document("doc_2", "Content 2", ticker="BBRI")

        # Save
        store1._save()

        # Create new store and load
        store2 = VectorStore(storage_path=temp_storage)
        store2._load()

        assert len(store2.documents) == 2
        assert "doc_1" in store2.documents
        assert "doc_2" in store2.documents

    def test_clear(self, temp_storage):
        """Test clearing all documents."""
        store = VectorStore(storage_path=temp_storage)
        store.add_document("doc_1", "Content 1")
        store.add_document("doc_2", "Content 2")

        store.clear()

        assert len(store.documents) == 0
        assert len(store.embeddings) == 0

    def test_search_no_results(self):
        """Test search with no matching documents."""
        store = VectorStore()
        results = store.search("unrelated topic")
        assert results == []


# =============================================================================
# TESTS FOR DOCUMENT PROCESSOR
# =============================================================================

class TestDocumentProcessor:
    """Tests for DocumentProcessor class."""

    def test_chunk_text_basic(self):
        """Test basic text chunking."""
        text = "This is a test document. It has multiple sentences. Each sentence should be chunked properly."
        chunks = DocumentProcessor.chunk_text(text, chunk_size=30, overlap=10)

        assert len(chunks) > 0
        for chunk in chunks:
            assert "content" in chunk
            assert "start" in chunk
            assert "end" in chunk

    def test_chunk_text_overlaps(self):
        """Test that chunks overlap correctly."""
        text = "A B C D E F G H I J K L M N O P"
        chunks = DocumentProcessor.chunk_text(text, chunk_size=10, overlap=5)

        assert len(chunks) >= 2, f"Expected at least 2 chunks, got {len(chunks)}"
        # Check overlap - second chunk should start before first ends
        if len(chunks) > 1:
            # The overlap means chunk2 starts 'overlap' chars before chunk1 ends
            expected_start = chunks[0]["end"] - 5  # overlap=5
            assert chunks[1]["start"] == expected_start, \
                f"Expected overlap: chunk1 end={chunks[0]['end']}, chunk2 start={chunks[1]['start']}, expected={expected_start}"
            assert chunks[0]["end"] > chunks[1]["start"], \
                f"No overlap: chunk1 ends at {chunks[0]['end']}, chunk2 starts at {chunks[1]['start']}"

    def test_chunk_text_small_chunks(self):
        """Test chunking with small chunk size."""
        text = "Short text"
        chunks = DocumentProcessor.chunk_text(text, chunk_size=100)

        assert len(chunks) == 1
        assert chunks[0]["content"] == text


# =============================================================================
# TESTS FOR CONVENIENCE FUNCTIONS
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_create_vector_store(self, temp_storage):
        """Test convenience function for creating store."""
        store = create_vector_store(storage_path=temp_storage)
        assert isinstance(store, VectorStore)

    def test_search_documents(self, temp_storage):
        """Test convenience function for searching."""
        store = create_vector_store(storage_path=temp_storage)
        store.add_document("doc_1", "Banking sector growth", ticker="BBCA")

        results = search_documents("banking growth", store, top_k=1)
        assert len(results) > 0


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for vector search."""

    def test_full_workflow(self, temp_storage):
        """Test complete workflow: add, search, retrieve."""
        store = VectorStore(storage_path=temp_storage)

        # Add documents
        store.add_document(
            "bbca_annual",
            "Bank Central Asia reported strong annual results with 12% revenue growth and ROE of 25%.",
            ticker="BBCA",
            doc_type="annual_report",
        )
        store.add_document(
            "bbri_news",
            "Bank Rakyat Indonesia launches new digital banking platform.",
            ticker="BBRI",
            doc_type="news",
        )

        # Search
        results = store.search("banking growth ROE", ticker="BBCA", top_k=1)
        assert len(results) > 0
        assert results[0]["ticker"] == "BBCA"

        # Verify persistence
        store._save()

        # Reload and verify
        store2 = VectorStore(storage_path=temp_storage)
        store2._load()
        assert len(store2.documents) == 2

    def test_rag_integration(self, temp_storage):
        """Test integration with RAG workflow."""
        store = VectorStore(storage_path=temp_storage)

        # Add contextual documents
        store.add_document(
            "context_1",
            "BBCA has consistently delivered ROE above 20% for the past 5 years.",
            ticker="BBCA",
            doc_type="analysis",
        )
        store.add_document(
            "context_2",
            "Indonesian banking sector faces margin pressure from competitive lending.",
            ticker=None,
            doc_type="market_report",
        )

        # Simulate RAG query
        query = "What is BBCA's historical ROE performance?"
        results = store.search(query, ticker="BBCA", top_k=1)

        assert len(results) > 0
        # Should find the relevant document
        assert "ROE" in results[0]["content"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
