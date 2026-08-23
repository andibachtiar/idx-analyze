"""
Data Loader Module for idx-bei investment research platform.

Loads data from scraped JSON files and provides it to the AI tools.
This bridges the gap between data collection and AI analysis.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Data directory (relative to project root)
DATA_DIR = Path(__file__).parent.parent.parent / "data"


class DataLoader:
    """
    Load and provide access to scraped financial data.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize data loader.

        Args:
            data_dir: Path to data directory (defaults to ./data/)
        """
        self.data_dir = data_dir or DATA_DIR
        self._cache: Dict[str, Any] = {}

    def _load_json(self, filename: str) -> Optional[Dict]:
        """Load a JSON file from data directory."""
        filepath = self.data_dir / filename
        if not filepath.exists():
            return None

        if filename in self._cache:
            return self._cache[filename]

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._cache[filename] = data
            return data
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            return None

    def get_company_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get company information for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with company info or None if not found
        """
        # Try loading company details
        data = self._load_json("companyDetailsByKodeEmiten.json")
        if not data:
            return None

        # Search for ticker (case-insensitive)
        ticker_upper = ticker.upper()
        for company in data:
            if company.get("kode_emiten", "").upper() == ticker_upper:
                return {
                    "ticker": ticker_upper,
                    "name": company.get("nama_perusahaan", ""),
                    "sector": company.get("sectors", ""),
                    "industry": company.get("industries", ""),
                    "listing_date": company.get("date_listing", ""),
                    "board": company.get("board", ""),
                }

        # Try all companies list
        all_companies = self._load_json("allCompanies.json")
        if all_companies:
            for company in all_companies:
                if company.get("KodeEmiten", "").upper() == ticker_upper:
                    return {
                        "ticker": ticker_upper,
                        "name": company.get("NamaEmiten", ""),
                        "sector": company.get("Sector", ""),
                        "industry": company.get("Industri", ""),
                    }

        return None

    def get_financial_ratios(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get financial ratios for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with financial ratios or None if not found
        """
        data = self._load_json("financial_ratio.json")
        if not data:
            return None

        ticker_upper = ticker.upper()

        # Handle wrapper object format {"totalRecords": N, "data": [...]}
        if isinstance(data, dict) and "data" in data:
            data = data["data"]

        # Handle both list and dict formats
        if isinstance(data, list):
            for item in data:
                # Check multiple possible ticker field names
                if (item.get("Symbol", "").upper() == ticker_upper or
                    item.get("ticker", "").upper() == ticker_upper or
                    item.get("code", "").upper() == ticker_upper):
                    return item
        elif isinstance(data, dict):
            if ticker_upper in data:
                return data[ticker_upper]
            # Try case-insensitive search
            for key in data:
                if key.upper() == ticker_upper:
                    return data[key]

        return None

    def get_stock_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get current stock price from index summary.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with price info or None
        """
        data = self._load_json("index_summary.json")
        if not data:
            return None

        ticker_upper = ticker.upper()

        # Search for ticker in index data
        if isinstance(data, list):
            for item in data:
                if item.get("KodeEmiten", "").upper() == ticker_upper or \
                   item.get("symbol", "").upper() == ticker_upper:
                    return {
                        "ticker": ticker_upper,
                        "price": item.get("Last", item.get("price")),
                        "change": item.get("Change", item.get("change")),
                        "change_pct": item.get("ChangePercent", item.get("change_percent")),
                        "volume": item.get("Volume", item.get("volume")),
                        "as_of": datetime.now().isoformat(),
                    }
        elif isinstance(data, dict):
            if ticker_upper in data:
                return data[ticker_upper]

        return None

    def get_company_summary(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get company summary from company summary file.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with company summary or None
        """
        data = self._load_json("companySummaryByKodeEmiten.json")
        if not data:
            return None

        ticker_upper = ticker.upper()

        if isinstance(data, list):
            for item in data:
                if item.get("KodeEmiten", "").upper() == ticker_upper:
                    return item

        return None

    def get_news(self, ticker: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent news articles.

        Args:
            ticker: Optional ticker to filter news
            limit: Maximum number of articles to return

        Returns:
            List of news articles
        """
        data = self._load_json("idx_news.json")
        if not data:
            return []

        news = data if isinstance(data, list) else data.get("news", [])

        # Filter by ticker if provided
        if ticker:
            ticker_upper = ticker.upper()
            news = [n for n in news if ticker_upper in n.get("symbols", []).upper()]

        # Limit results
        return news[:limit]

    def get_all_tickers(self) -> List[str]:
        """
        Get list of all tracked tickers.

        Returns:
            List of ticker symbols
        """
        data = self._load_json("allCompanies.json")
        if not data:
            return []

        return [c.get("KodeEmiten", "") for c in data if c.get("KodeEmiten")]

    def has_data(self, ticker: str) -> bool:
        """
        Check if data exists for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            True if any data exists for this ticker
        """
        return (
            self.get_company_info(ticker) is not None or
            self.get_financial_ratios(ticker) is not None or
            self.get_stock_price(ticker) is not None
        )

    def get_data_status(self, ticker: str) -> Dict[str, bool]:
        """
        Get status of available data for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary showing which data types are available
        """
        return {
            "company_info": self.get_company_info(ticker) is not None,
            "financial_ratios": self.get_financial_ratios(ticker) is not None,
            "stock_price": self.get_stock_price(ticker) is not None,
            "news": len(self.get_news(ticker)) > 0,
        }


# Global data loader instance
_data_loader: Optional[DataLoader] = None


def get_data_loader() -> DataLoader:
    """
    Get the global data loader instance.

    Returns:
        DataLoader instance
    """
    global _data_loader
    if _data_loader is None:
        _data_loader = DataLoader()
    return _data_loader


def reset_data_loader():
    """Reset the global data loader (for testing)."""
    global _data_loader
    _data_loader = None
