"""
PostgreSQL Data Loader for idx-bei investment research platform.

Loads data from PostgreSQL database instead of JSON files.
This provides better query capabilities, concurrency, and scalability.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None


class PostgreSQLDataLoader:
    """
    Load financial data from PostgreSQL database.
    """

    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize data loader with database connection.

        Args:
            db_url: PostgreSQL connection URL (defaults to DATABASE_URL env var)
        """
        self.db_url = db_url or os.environ.get("DATABASE_URL", "")
        self._conn = None

    def _get_connection(self):
        """Get or create database connection."""
        if self._conn is None or self._conn.closed:
            if psycopg2 is None:
                raise ImportError("psycopg2 not installed. Run: pip install psycopg2-binary")
            if not self.db_url:
                raise ValueError("DATABASE_URL not set in environment")
            self._conn = psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
        return self._conn

    def get_company_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get company information from database."""
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT ticker, name, sector, industry, listing_date, board FROM companies WHERE ticker = %s",
                    (ticker.upper(),)
                )
                row = cur.fetchone()
                if row:
                    return {
                        "ticker": row["ticker"],
                        "name": row["name"],
                        "sector": row["sector"],
                        "industry": row["industry"],
                        "listing_date": str(row["listing_date"]) if row["listing_date"] else "",
                        "board": row["board"],
                    }
                return None
        except Exception as e:
            print(f"Error getting company info: {e}")
            return None

    def get_financial_ratios(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get latest financial ratios from database."""
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM financial_ratios
                    WHERE ticker = %s
                    ORDER BY fiscal_year DESC, fiscal_period DESC NULLS LAST
                    LIMIT 1
                """, (ticker.upper(),))
                row = cur.fetchone()
                if row:
                    # Convert numeric values to float for easier handling
                    result = dict(row)
                    for key in ['roe', 'roa', 'gross_margin', 'operating_margin', 'net_margin',
                                'debt_to_equity', 'current_ratio', 'pe_ratio', 'pb_ratio']:
                        if result.get(key) is not None:
                            result[key] = float(result[key])
                    return result
                return None
        except Exception as e:
            print(f"Error getting financial ratios: {e}")
            return None

    def get_stock_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get latest stock price from database."""
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ticker, trading_date, close_price, volume
                    FROM stock_prices
                    WHERE ticker = %s
                    ORDER BY trading_date DESC
                    LIMIT 1
                """, (ticker.upper(),))
                row = cur.fetchone()
                if row:
                    return {
                        "ticker": row["ticker"],
                        "price": int(row["close_price"]) if row["close_price"] else None,
                        "volume": int(row["volume"]) if row["volume"] else None,
                        "as_of": str(row["trading_date"]),
                    }
                return None
        except Exception as e:
            print(f"Error getting stock price: {e}")
            return None

    def get_historical_prices(self, ticker: str, days: int = 100) -> List[Dict[str, Any]]:
        """Get historical stock prices for technical analysis."""
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT trading_date, close_price, volume
                    FROM stock_prices
                    WHERE ticker = %s
                    ORDER BY trading_date DESC
                    LIMIT %s
                """, (ticker.upper(), days))
                rows = cur.fetchall()
                return [
                    {
                        "date": str(r["trading_date"]),
                        "price": int(r["close_price"]) if r["close_price"] else None,
                        "volume": int(r["volume"]) if r["volume"] else None,
                    }
                    for r in rows
                ]
        except Exception as e:
            print(f"Error getting historical prices: {e}")
            return []

    def list_stocks(self) -> List[Dict[str, Any]]:
        """List all companies with their latest close price and metadata."""
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    WITH latest AS (
                        SELECT p.ticker,
                               ROW_NUMBER() OVER (PARTITION BY p.ticker ORDER BY p.trading_date DESC) AS rn,
                               p.trading_date, p.close_price, p.open_price, p.high_price, p.low_price, p.volume
                        FROM stock_prices p
                    )
                    SELECT c.ticker, c.name, c.sector, c.industry,
                           sp.trading_date, sp.close_price, sp.open_price,
                           sp.high_price, sp.low_price, sp.volume,
                           prev.close_price AS prev_close
                    FROM companies c
                    LEFT JOIN latest sp ON sp.ticker = c.ticker AND sp.rn = 1
                    LEFT JOIN latest prev ON prev.ticker = c.ticker AND prev.rn = 2
                    ORDER BY c.ticker
                """)
                rows = cur.fetchall()
            result = []
            for r in rows:
                close = float(r["close_price"]) if r["close_price"] is not None else None
                prev = float(r["prev_close"]) if r["prev_close"] is not None else None
                change = (close - prev) if (close is not None and prev is not None) else None
                change_pct = (change / prev * 100) if (change is not None and prev) else None
                result.append({
                    "ticker": r["ticker"],
                    "name": r["name"],
                    "sector": r["sector"],
                    "industry": r["industry"],
                    "date": str(r["trading_date"]) if r["trading_date"] else None,
                    "close": close,
                    "open": float(r["open_price"]) if r["open_price"] is not None else None,
                    "high": float(r["high_price"]) if r["high_price"] is not None else None,
                    "low": float(r["low_price"]) if r["low_price"] is not None else None,
                    "volume": int(r["volume"]) if r["volume"] is not None else None,
                    "change": change,
                    "change_pct": change_pct,
                })
            return result
        except Exception as e:
            print(f"Error listing stocks: {e}")
            return []

    def list_stock_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Return the latest financial ratios for every ticker as a screening map.

        The result is shaped like ``{ticker: {metric_name: value}}`` so it can be
        passed straight into ``ai.tools.run_screening`` (``stocks`` argument).
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT ON (ticker) ticker,
                           revenue, eps, total_assets, total_equity, total_debt,
                           gross_margin, operating_margin, net_margin,
                           roe, roa, roic, debt_to_equity, current_ratio,
                           interest_coverage, pe_ratio, pb_ratio, ev_ebitda,
                           dividend_yield, payout_ratio, revenue_cagr, earnings_cagr
                    FROM financial_ratios
                    ORDER BY ticker, fiscal_year DESC, fiscal_period DESC NULLS LAST
                """)
                rows = cur.fetchall()
            metrics: Dict[str, Dict[str, Any]] = {}
            for r in rows:
                d = dict(r)
                ticker = d.pop("ticker")
                metrics[ticker] = {
                    k: (float(v) if v is not None else None)
                    for k, v in dict(d).items()
                }
            return metrics
        except Exception as e:
            print(f"Error listing stock metrics: {e}")
            return {}

    def get_price_history(
        self,
        ticker: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """Return ordered OHLCV history for a ticker (oldest first)."""
        try:
            conn = self._get_connection()
            conditions = ["ticker = %s"]
            params: list[Any] = [ticker.upper()]
            if start:
                conditions.append("trading_date >= %s")
                params.append(start)
            if end:
                conditions.append("trading_date <= %s")
                params.append(end)
            # For the most-recent `limit` rows, fetch the whole window then slice.
            params.append(limit)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT trading_date, open_price, high_price, low_price, close_price, volume
                    FROM stock_prices
                    WHERE """
                    + " AND ".join(conditions)
                    + " ORDER BY trading_date DESC LIMIT %s",
                    params,
                )
                rows = cur.fetchall()
            rows.reverse()  # oldest -> newest for charting
            return [
                {
                    "date": str(r["trading_date"]),
                    "open": float(r["open_price"]) if r["open_price"] is not None else None,
                    "high": float(r["high_price"]) if r["high_price"] is not None else None,
                    "low": float(r["low_price"]) if r["low_price"] is not None else None,
                    "close": float(r["close_price"]) if r["close_price"] is not None else None,
                    "volume": int(r["volume"]) if r["volume"] is not None else None,
                }
                for r in rows
            ]
        except Exception as e:
            print(f"Error getting price history: {e}")
            return []

    def get_news(self, ticker: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent news articles."""
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                if ticker:
                    cur.execute("""
                        SELECT ticker, title, content, source, published_at, url, sentiment_score
                        FROM news_articles
                        WHERE ticker = %s
                        ORDER BY published_at DESC
                        LIMIT %s
                    """, (ticker.upper(), limit))
                else:
                    cur.execute("""
                        SELECT ticker, title, content, source, published_at, url, sentiment_score
                        FROM news_articles
                        ORDER BY published_at DESC
                        LIMIT %s
                    """, (limit,))

                rows = cur.fetchall()
                return [
                    {
                        "ticker": r["ticker"],
                        "title": r["title"],
                        "content": r["content"],
                        "source": r["source"],
                        "published_at": str(r["published_at"]) if r["published_at"] else "",
                        "url": r["url"],
                        "sentiment": float(r["sentiment_score"]) if r["sentiment_score"] else None,
                    }
                    for r in rows
                ]
        except Exception as e:
            print(f"Error getting news: {e}")
            return []

    def has_data(self, ticker: str) -> bool:
        """Check if data exists for a ticker."""
        return (
            self.get_company_info(ticker) is not None or
            self.get_financial_ratios(ticker) is not None or
            self.get_stock_price(ticker) is not None
        )

    def get_data_status(self, ticker: str) -> Dict[str, bool]:
        """Get status of available data for a ticker."""
        return {
            "company_info": self.get_company_info(ticker) is not None,
            "financial_ratios": self.get_financial_ratios(ticker) is not None,
            "stock_price": self.get_stock_price(ticker) is not None,
            "news": len(self.get_news(ticker)) > 0,
        }

    def close(self):
        """Close database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()
            self._conn = None


# Global instance
_db_loader: Optional[PostgreSQLDataLoader] = None


def get_data_loader() -> PostgreSQLDataLoader:
    """Get the global database data loader instance."""
    global _db_loader
    if _db_loader is None:
        _db_loader = PostgreSQLDataLoader()
    return _db_loader


def reset_data_loader():
    """Reset the global data loader (for testing)."""
    global _db_loader
    if _db_loader:
        _db_loader.close()
    _db_loader = None
