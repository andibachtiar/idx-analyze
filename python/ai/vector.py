"""
Vector Search Module for idx-bei investment research platform.

Provides semantic search over unstructured documents such as:
- Annual reports
- PDFs
- Earnings presentations
- Corporate announcements
- News articles
- Management commentary

This module uses embeddings to enable semantic search, NOT for storing
structured financial metrics (those remain in PostgreSQL/Neo4j).
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class VectorStore:
    """
    Simple vector store for document embeddings.

    Supports:
    - In-memory storage (default)
    - JSON file persistence
    - Semantic search via cosine similarity
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
        use_embedding_model: bool = True,
        embedding_model: str = "text-embedding-3-small",
    ):
        """
        Initialize vector store.

        Args:
            storage_path: Path to JSON file for persistence
            use_embedding_model: Whether to use OpenAI embeddings
            embedding_model: Name of embedding model to use
        """
        self.storage_path = Path(storage_path) if storage_path else None
        self.use_embedding_model = use_embedding_model
        self.embedding_model = embedding_model
        self._client = None

        if use_embedding_model and OpenAI is not None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                self._client = OpenAI(api_key=api_key)

        # In-memory storage
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.embeddings: Dict[str, List[float]] = {}

        # Load from file if exists
        if self.storage_path and self.storage_path.exists():
            self._load()

    @property
    def client(self):
        """Get OpenAI client."""
        return self._client

    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text using OpenAI API.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if unavailable
        """
        if not self._client:
            return None

        try:
            response = self._client.embeddings.create(
                input=text,
                model=self.embedding_model,
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Embedding generation failed: {e}")
            return None

    def _simple_embedding(self, text: str, dimension: int = 128) -> List[float]:
        """
        Generate a simple deterministic embedding for testing.

        This creates a fixed-length vector based on text content.
        NOT suitable for production - use OpenAI embeddings instead.
        """
        # Create deterministic hash-based embedding
        hash_val = hash(text)
        rng = np.random.RandomState(abs(hash_val) % (2**32))
        return rng.rand(dimension).tolist()

    def add_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        ticker: Optional[str] = None,
        doc_type: str = "general",
    ) -> bool:
        """
        Add a document to the vector store.

        Args:
            doc_id: Unique identifier for the document
            content: Text content of the document
            metadata: Additional metadata
            ticker: Related stock ticker (if any)
            doc_type: Type of document (annual_report, news, earnings, etc.)

        Returns:
            True if added successfully
        """
        # Generate embedding
        if self.use_embedding_model and self._client:
            embedding = self._generate_embedding(content)
        else:
            embedding = self._simple_embedding(content)

        if embedding is None:
            return False

        # Store document
        self.documents[doc_id] = {
            "id": doc_id,
            "content": content,
            "metadata": metadata or {},
            "ticker": ticker,
            "doc_type": doc_type,
            "added_at": datetime.now().isoformat(),
        }
        self.embeddings[doc_id] = embedding

        # Save to file if path configured
        if self.storage_path:
            self._save()

        return True

    def remove_document(self, doc_id: str) -> bool:
        """
        Remove a document from the vector store.

        Args:
            doc_id: Document identifier

        Returns:
            True if removed
        """
        if doc_id in self.documents:
            del self.documents[doc_id]
            del self.embeddings[doc_id]
            if self.storage_path:
                self._save()
            return True
        return False

    def search(
        self,
        query: str,
        top_k: int = 5,
        ticker: Optional[str] = None,
        doc_type: Optional[str] = None,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Search for documents similar to query.

        Args:
            query: Search query text
            top_k: Number of results to return
            ticker: Filter by ticker
            doc_type: Filter by document type
            min_score: Minimum similarity score

        Returns:
            List of matching documents with scores
        """
        # Generate query embedding
        if self.use_embedding_model and self._client:
            query_embedding = self._generate_embedding(query)
        else:
            query_embedding = self._simple_embedding(query)

        if query_embedding is None:
            return []

        query_vec = np.array(query_embedding)

        # Calculate similarities
        results = []
        for doc_id, doc in self.documents.items():
            # Apply filters
            if ticker and doc.get("ticker") != ticker.upper():
                continue
            if doc_type and doc.get("doc_type") != doc_type:
                continue

            # Calculate cosine similarity
            doc_vec = np.array(self.embeddings[doc_id])
            similarity = np.dot(query_vec, doc_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(doc_vec)
            )

            if similarity >= min_score:
                results.append({
                    "doc_id": doc_id,
                    "score": float(similarity),
                    "content": doc["content"],
                    "ticker": doc.get("ticker"),
                    "doc_type": doc.get("doc_type") or "general",
                    "added_at": doc.get("added_at") or datetime.now().isoformat(),
                })

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:top_k]

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by ID.

        Args:
            doc_id: Document identifier

        Returns:
            Document dict or None
        """
        return self.documents.get(doc_id)

    def get_documents_by_ticker(
        self,
        ticker: str,
        doc_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all documents for a ticker.

        Args:
            ticker: Stock ticker symbol
            doc_type: Optional filter by document type

        Returns:
            List of documents
        """
        ticker_upper = ticker.upper()
        results = []

        for doc_id, doc in self.documents.items():
            if doc.get("ticker") == ticker_upper:
                if doc_type is None or doc.get("doc_type") == doc_type:
                    results.append(doc)

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.

        Returns:
            Dictionary with usage statistics
        """
        ticker_counts: Dict[str, int] = {}
        type_counts: Dict[str, int] = {}

        for doc in self.documents.values():
            ticker = doc.get("ticker", "unknown")
            doc_type = doc.get("doc_type", "unknown")
            ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1

        return {
            "total_documents": len(self.documents),
            "tickers": ticker_counts,
            "document_types": type_counts,
        }

    def _save(self):
        """Save store to JSON file."""
        if not self.storage_path:
            return

        data = {
            "documents": self.documents,
            "embeddings": {k: v for k, v in self.embeddings.items()},
            "saved_at": datetime.now().isoformat(),
        }

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

    def _load(self):
        """Load store from JSON file."""
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.documents = data.get("documents", {})
            self.embeddings = {k: v for k, v in data.get("embeddings", {}).items()}
        except (json.JSONDecodeError, IOError):
            pass

    def clear(self):
        """Clear all documents from the store."""
        self.documents.clear()
        self.embeddings.clear()
        if self.storage_path:
            if self.storage_path.exists():
                self.storage_path.unlink()


# =============================================================================
# DOCUMENT PROCESSORS
# =============================================================================

class DocumentProcessor:
    """
    Processes and chunks documents for vector storage.
    """

    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks.

        Args:
            text: Input text
            chunk_size: Maximum characters per chunk
            overlap: Characters to overlap between chunks

        Returns:
            List of chunk dictionaries
        """
        chunks = []
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)

                if break_point > chunk_size * 0.5:
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1

            chunks.append({
                "content": chunk.strip(),
                "start": start,
                "end": end,
            })

            # Break if we've reached the end of the text
            if end >= len(text):
                break

            start = end - overlap
            # Safety check to prevent infinite loop
            if start <= 0:
                start = end
                break

        return chunks


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_vector_store(
    storage_path: Optional[str] = None,
    use_openai: bool = True,
) -> VectorStore:
    """
    Convenience function to create a vector store.

    Args:
        storage_path: Path for persistent storage
        use_openai: Whether to use OpenAI embeddings

    Returns:
        VectorStore instance
    """
    return VectorStore(
        storage_path=storage_path,
        use_embedding_model=use_openai,
    )


def search_documents(
    query: str,
    vector_store: VectorStore,
    ticker: Optional[str] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Convenience function to search documents.

    Args:
        query: Search query
        vector_store: VectorStore instance
        ticker: Optional ticker filter
        top_k: Number of results

    Returns:
        List of matching documents
    """
    return vector_store.search(query, top_k=top_k, ticker=ticker)
