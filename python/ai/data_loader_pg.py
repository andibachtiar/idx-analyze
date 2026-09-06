"""
PostgreSQL Data Loader for idx-bei investment research platform.

Loads data from PostgreSQL database instead of JSON files.
This provides better query capabilities, concurrency, and scalability.
"""

from __future__ import annotations

import functools
import hashlib
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None


def _ttl_cache(method):
    """Cache a read-only loader method result for CACHE_TTL seconds.

    Keys on (method name, args) so per-ticker queries stay distinct. A TTL of
    0 (DATA_CACHE_TTL=0) disables caching entirely. The cache lives in the
    process; scrapers write via ``ScraperDatabase`` and the scheduler calls
    ``clear_cache`` after a pipeline run so the API sees fresh data.
    """

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if getattr(self, "_cache_ttl", 0) <= 0:
            return method(self, *args, **kwargs)
        key = _cache_key(method.__name__, args, kwargs)
        now = time.time()
        entry = self._cache.get(key)
        if entry is not None and entry[0] > now:
            return entry[1]
        result = method(self, *args, **kwargs)
        self._cache[key] = (now + self._cache_ttl, result)
        return result

    return wrapper


def _cache_key(name: str, args: tuple, kwargs: dict) -> str:
    parts = [name, repr(args), repr(sorted(kwargs.items()))]
    return hashlib.sha1("|".join(parts).encode("utf-8", errors="ignore")).hexdigest()


def _wilder_rsi(closes: list[float], period: int = 14) -> float | None:
    """Wilder's RSI over ``closes`` (chronological). Returns None if too short."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0.0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


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
        # Phase 26: simple in-process TTL cache for hot read methods.
        self._cache_ttl = int(os.environ.get("DATA_CACHE_TTL", "60"))
        self._cache: dict[str, tuple[float, Any]] = {}

    def clear_cache(self) -> None:
        """Drop all cached reads (called after a pipeline run / manual refresh)."""
        self._cache.clear()

    def _get_connection(self):
        """Get or create database connection."""
        if self._conn is None or self._conn.closed:
            if psycopg2 is None:
                raise ImportError("psycopg2 not installed. Run: pip install psycopg2-binary")
            if not self.db_url:
                raise ValueError("DATABASE_URL not set in environment")
            self._conn = psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
        return self._conn

    @_ttl_cache
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

    @_ttl_cache
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

    @_ttl_cache
    def get_financial_ratios_merged(self, ticker: str) -> Dict[str, Any]:
        """Merge the latest non-null ratio across all stored periods for a ticker.

        Different periods carry different fields (e.g. the IDX row has P/E, ROE,
        D/E while the yfinance backfill row has revenue/margins), so a simple
        ``ORDER BY ... LIMIT 1`` can return a sparse row. This walks newest->oldest
        and keeps the first non-null value per field, giving the most complete
        snapshot for a fundamentals interpretation.
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM financial_ratios
                    WHERE ticker = %s
                    ORDER BY fiscal_year DESC, fiscal_period DESC NULLS LAST
                """, (ticker.upper(),))
                rows = cur.fetchall()
            merged: Dict[str, Any] = {}
            for row in rows:
                for key, value in dict(row).items():
                    if value is not None and merged.get(key) is None:
                        if isinstance(value, (int, float)):
                            merged[key] = float(value)
                        else:
                            # Dates, ticker, source stay as-is; only cast numeric strings.
                            try:
                                merged[key] = float(value)
                            except (TypeError, ValueError):
                                merged[key] = value
            return merged
        except Exception as e:
            print(f"Error merging financial ratios: {e}")
            return {}

    @_ttl_cache
    def get_financial_ratio_history(self, ticker: str) -> List[Dict[str, Any]]:
        """Return all stored financial_ratios for a ticker, oldest first.

        Used by the finance fundamentals chart (revenue/earnings/margins over
        multiple fiscal periods). Numeric values are converted to float so the
        frontend can plot them directly; missing values stay ``None``.
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT fiscal_year, fiscal_period, period_end,
                           revenue, gross_margin, operating_margin, net_margin,
                           operating_income, net_income, eps,
                           total_assets, total_liabilities, total_equity, total_debt,
                           roe, roa, roic, debt_to_equity, current_ratio,
                           pe_ratio, pb_ratio, ev_ebitda, dividend_yield,
                           revenue_cagr, earnings_cagr
                    FROM financial_ratios
                    WHERE ticker = %s
                    ORDER BY period_end ASC NULLS LAST, fiscal_year ASC, fiscal_period ASC NULLS LAST
                """, (ticker.upper(),))
                rows = cur.fetchall()
            return [
                {
                    "fiscal_year": r["fiscal_year"],
                    "fiscal_period": r["fiscal_period"],
                    "period_end": str(r["period_end"]) if r["period_end"] else None,
                    "revenue": float(r["revenue"]) if r["revenue"] is not None else None,
                    "gross_margin": float(r["gross_margin"]) if r["gross_margin"] is not None else None,
                    "operating_margin": float(r["operating_margin"]) if r["operating_margin"] is not None else None,
                    "net_margin": float(r["net_margin"]) if r["net_margin"] is not None else None,
                    "operating_income": float(r["operating_income"]) if r["operating_income"] is not None else None,
                    "net_income": float(r["net_income"]) if r["net_income"] is not None else None,
                    "eps": float(r["eps"]) if r["eps"] is not None else None,
                    "total_assets": float(r["total_assets"]) if r["total_assets"] is not None else None,
                    "total_liabilities": float(r["total_liabilities"]) if r["total_liabilities"] is not None else None,
                    "total_equity": float(r["total_equity"]) if r["total_equity"] is not None else None,
                    "total_debt": float(r["total_debt"]) if r["total_debt"] is not None else None,
                    "roe": float(r["roe"]) if r["roe"] is not None else None,
                    "roa": float(r["roa"]) if r["roa"] is not None else None,
                    "roic": float(r["roic"]) if r["roic"] is not None else None,
                    "debt_to_equity": float(r["debt_to_equity"]) if r["debt_to_equity"] is not None else None,
                    "current_ratio": float(r["current_ratio"]) if r["current_ratio"] is not None else None,
                    "pe_ratio": float(r["pe_ratio"]) if r["pe_ratio"] is not None else None,
                    "pb_ratio": float(r["pb_ratio"]) if r["pb_ratio"] is not None else None,
                    "ev_ebitda": float(r["ev_ebitda"]) if r["ev_ebitda"] is not None else None,
                    "dividend_yield": float(r["dividend_yield"]) if r["dividend_yield"] is not None else None,
                    "revenue_cagr": float(r["revenue_cagr"]) if r["revenue_cagr"] is not None else None,
                    "earnings_cagr": float(r["earnings_cagr"]) if r["earnings_cagr"] is not None else None,
                }
                for r in rows
            ]
        except Exception as e:
            print(f"Error getting financial ratio history: {e}")
            return []

    @_ttl_cache
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

    @_ttl_cache
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

    @_ttl_cache
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

    @_ttl_cache
    def list_stock_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Return per-ticker financial ratios as a screening map, merged across periods.

        Different periods carry different fields: the yfinance backfill row holds
        dividend_yield / payout_ratio / margins while the IDX row holds roe / pe
        / debt_to_equity. Picking only the newest row (``DISTINCT ON``) would
        fragment these and make screens (Dividend/Value/Quality/…) return zero.
        This walks newest->oldest per ticker and keeps the first non-null value
        per field, giving the most complete snapshot for screening.

        Result shape: ``{ticker: {metric_name: value}}``.
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ticker,
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
                merged = metrics.setdefault(ticker, {})
                for k, v in d.items():
                    if v is not None and merged.get(k) is None:
                        merged[k] = float(v)
            # Normalise percent-ratio fields to decimals so screen thresholds
            # (roe >= 0.15, net_margin >= 0.10, etc.) are in the same convention.
            # dividend_yield stays percent (screens use >= 3.0) and CAGR stays
            # decimal (screens use >= 0.10).
            percent_fields = {"roe", "roa", "roic", "gross_margin", "operating_margin", "net_margin"}
            for merged in metrics.values():
                for field in percent_fields:
                    if merged.get(field) is not None:
                        merged[field] /= 100.0
            return metrics
        except Exception as e:
            print(f"Error listing stock metrics: {e}")
            return {}

    @_ttl_cache
    def list_technical_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Return per-ticker technical indicators from price history for screening.

        Computes ``close``, ``price_vs_sma_200`` ((close - sma200)/sma200),
        ``rsi_14``, and ``volume_ratio`` (latest vol / 20-day mean vol) for every
        ticker with enough history. Used by the ``technical`` screen which filters
        on those fields. Cached via ``_ttl_cache`` since it scans 1M+ rows.
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ticker, trading_date, close_price, volume
                    FROM stock_prices
                    ORDER BY ticker, trading_date ASC
                """)
                rows = cur.fetchall()
            series: Dict[str, Dict[str, list]] = {}
            for r in rows:
                t = r["ticker"]
                close = r["close_price"]
                if close is None:
                    continue
                s = series.setdefault(t, {"closes": [], "volumes": []})
                s["closes"].append(float(close))
                s["volumes"].append(float(r["volume"]) if r["volume"] is not None else 0.0)
            out: Dict[str, Dict[str, Any]] = {}
            for ticker, s in series.items():
                closes = s["closes"]
                if len(closes) < 200:
                    continue
                sma200 = _mean(closes[-200:])
                close = closes[-1]
                price_vs = ((close - sma200) / sma200) if sma200 else None
                volumes = s["volumes"]
                vol_ratio = (
                    (volumes[-1] / _mean(volumes[-21:-1]))
                    if len(volumes) > 21 and _mean(volumes[-21:-1])
                    else None
                )
                out[ticker] = {
                    "close": close,
                    "price_vs_sma_200": price_vs,
                    "rsi_14": _wilder_rsi(closes[-260:]),
                    "volume_ratio": vol_ratio,
                }
            return out
        except Exception as e:
            print(f"Error listing technical metrics: {e}")
            return {}

    @_ttl_cache
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

    @_ttl_cache
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

    @_ttl_cache
    def get_news_impacts(
        self,
        hours: int = 48,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """Return deterministic news->sector/ticker impact tags within the last ``hours``.

        Each item carries the impacted sector/direction/confidence plus the source
        news headline and URL, so the LLM interpretation is grounded in evidence
        that was already computed deterministically (B3).
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT i.sector, i.ticker, i.direction, i.confidence,
                           i.matched_keywords,
                           n.title, n.url, n.source, n.published_at
                    FROM news_impacts i
                    JOIN news_articles n ON n.id = i.news_id
                    WHERE n.published_at >= NOW() - CONCAT(%s, ' hours')::interval
                    ORDER BY n.published_at DESC, i.confidence DESC
                    LIMIT %s
                    """,
                    (hours, limit),
                )
                rows = cur.fetchall()
                return [
                    {
                        "sector": r["sector"],
                        "ticker": r["ticker"],
                        "direction": r["direction"],
                        "confidence": float(r["confidence"]) if r["confidence"] is not None else None,
                        "matched_keywords": r["matched_keywords"],
                        "title": r["title"],
                        "url": r["url"],
                        "source": r["source"],
                        "published_at": str(r["published_at"]) if r["published_at"] else "",
                    }
                    for r in rows
                ]
        except Exception as e:
            print(f"Error getting news impacts: {e}")
            return []

    @_ttl_cache
    def get_research_candidates(
        self,
        hours: int = 48,
        status: Optional[str] = None,
        limit: int = 50,
        ticker: Optional[str] = None,
        sector: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return deterministic research candidates (Fase B5) within ``hours``.

        Sector/tickers are never invented by the LLM; they come from
        news_impacts snapshot. When ``ticker`` and/or ``sector`` are supplied the
        list is filtered to candidates that match that ticker directly or belong
        to that sector (so a stock's Research tab only shows its own industry).
        The daily ``llm_interpretation`` is carried on each row.
        """
        try:
            conn = self._get_connection()
            query = (
                "SELECT candidate_date, sector, ticker, direction, confidence, "
                "net_strength, reason, status, llm_interpretation "
                "FROM research_candidates "
                "WHERE candidate_date >= CURRENT_DATE - CONCAT(%s, ' hours')::interval "
            )
            params: list = [hours]
            if status:
                query += "AND status = %s "
                params.append(status)
            if ticker or sector:
                conditions = []
                if ticker:
                    conditions.append("ticker = %s")
                    params.append(ticker.upper())
                if sector:
                    conditions.append("sector = %s")
                    params.append(sector)
                query += "AND (" + " OR ".join(conditions) + ") "
            query += (
                "ORDER BY candidate_date DESC, ABS(net_strength) DESC, sector ASC "
                "LIMIT %s"
            )
            params.append(limit)
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                return [
                    {
                        "candidate_date": str(r["candidate_date"]),
                        "sector": r["sector"],
                        "ticker": r["ticker"],
                        "direction": r["direction"],
                        "confidence": float(r["confidence"]) if r["confidence"] is not None else None,
                        "net_strength": float(r["net_strength"]) if r["net_strength"] is not None else None,
                        "reason": r["reason"],
                        "status": r["status"],
                        "llm_interpretation": r["llm_interpretation"],
                    }
                    for r in rows
                ]
        except Exception as e:
            print(f"Error getting research candidates: {e}")
            return []

    @_ttl_cache
    def get_sector_tickers(
        self,
        sector: str,
        limit: int = 5,
    ) -> List[str]:
        """Return the most liquid tickers in a sector (deterministic, capped).

        Used to expand a sector-level macro candidate into stock-level candidates
        without bloating ``news_impacts``. Liquidity proxy = latest close * volume
        from ``stock_prices``; tickers with no price data fall back to "na" so they
        sort last. Deterministic tie-break by ticker ASC.
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.ticker,
                           COALESCE(p.close_price, 0) * COALESCE(p.volume, 0) AS liq
                    FROM companies c
                    LEFT JOIN LATERAL (
                        SELECT close_price, volume
                        FROM stock_prices
                        WHERE ticker = c.ticker
                        ORDER BY trading_date DESC
                        LIMIT 1
                    ) p ON true
                    WHERE c.sector = %s
                    ORDER BY liq DESC, c.ticker ASC
                    LIMIT %s
                    """,
                    (sector, limit),
                )
                return [r["ticker"] for r in cur.fetchall()]
        except Exception as e:
            print(f"Error getting sector tickers: {e}")
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


def clear_cache() -> None:
    """Clear the global loader read cache (call after a pipeline run / manual refresh)."""
    get_data_loader().clear_cache()


def reset_data_loader():
    """Reset the global data loader (for testing)."""
    global _db_loader
    if _db_loader:
        _db_loader.close()
    _db_loader = None
