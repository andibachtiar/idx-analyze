"""Shared PostgreSQL persistence for scraper output.

Scrapers use this module as their primary sink. Raw JSON files are optional
backups and are controlled by SCRAPER_SAVE_JSON.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:  # pragma: no cover
    psycopg2 = None
    execute_values = None


class ScraperDatabase:
    """Small database adapter used by scraper scripts."""

    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.getenv("DATABASE_URL", "")
        self.connection = None

    def connect(self) -> None:
        if psycopg2 is None:
            raise RuntimeError("psycopg2 is not installed; run uv sync")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is not set in the project .env")
        self.connection = psycopg2.connect(self.database_url)

    def close(self) -> None:
        if self.connection and not self.connection.closed:
            self.connection.close()
        self.connection = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.connection:
            if exc_type:
                self.connection.rollback()
            self.close()

    def upsert_companies(self, records: Iterable[dict[str, Any]]) -> int:
        rows = []
        for record in records:
            profile = record
            if isinstance(record, dict) and record.get("Profiles"):
                profile = record["Profiles"][0]
            ticker = profile.get("KodeEmiten") or profile.get("code")
            if not ticker or not profile.get("NamaEmiten") and not profile.get("stockName"):
                continue
            rows.append((
                str(ticker).upper(),
                profile.get("NamaEmiten") or profile.get("stockName") or str(ticker),
                profile.get("Sektor") or profile.get("sector"),
                profile.get("Industri") or profile.get("industry"),
                profile.get("SubIndustri") or profile.get("subIndustry"),
                _date(profile.get("TanggalPencatatan") or profile.get("listing_date")),
                profile.get("PapanPencatatan") or profile.get("board"),
            ))
        if not rows:
            return 0
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            execute_values(cursor, """
                INSERT INTO companies
                    (ticker, name, sector, industry, sub_industry, listing_date, board)
                VALUES %s
                ON CONFLICT (ticker) DO UPDATE SET
                    name = EXCLUDED.name,
                    sector = EXCLUDED.sector,
                    industry = EXCLUDED.industry,
                    sub_industry = EXCLUDED.sub_industry,
                    listing_date = EXCLUDED.listing_date,
                    board = EXCLUDED.board,
                    updated_at = CURRENT_TIMESTAMP
            """, rows)
        self.connection.commit()
        return len(rows)

    def upsert_financial_ratios(self, records: Iterable[dict[str, Any]]) -> int:
        records = list(records)
        # Ensure referenced company rows exist before inserting ratios.
        # Deduplicate by ticker so a batch of periods for the same company
        # doesn't violate ON CONFLICT DO UPDATE (a row can only be affected
        # once per command).
        companies = []
        seen_tickers = set()
        for item in records:
            ticker = item.get("code") or item.get("ticker") or item.get("Symbol")
            if ticker and ticker.upper() not in seen_tickers:
                seen_tickers.add(ticker.upper())
                companies.append({
                    "KodeEmiten": ticker,
                    "NamaEmiten": item.get("stockName") or ticker,
                    "Sektor": item.get("sector"),
                    "Industri": item.get("industry"),
                    "SubIndustri": item.get("subIndustry"),
                })
        self.upsert_companies(companies)

        rows = []
        for item in records:
            ticker = item.get("code") or item.get("ticker") or item.get("Symbol")
            if not ticker:
                continue
            period_end = _date(item.get("fsDate") or item.get("period_end"))
            fiscal_year = _int(item.get("fiscalYear")) or (period_end.year if period_end else None)
            rows.append((
                str(ticker).upper(), fiscal_year, _int(item.get("fiscalPeriod")), period_end,
                _number(item.get("sales")), _number(item.get("cogs")), _number(item.get("grossProfit")),
                _number(item.get("ebt")), _number(item.get("profitAttrOwner") or item.get("profitPeriod")),
                _number(item.get("eps")), _number(item.get("assets")), _number(item.get("liabilities")),
                _number(item.get("equity")), _number(item.get("cash")), _number(item.get("debt")),
                _number(item.get("grossMargin")), _number(item.get("operatingMargin")), _number(item.get("npm")),
                _number(item.get("roe")), _number(item.get("roa")), _number(item.get("roic")),
                _number(item.get("deRatio")), _number(item.get("currentRatio")), _number(item.get("interestCoverage")),
                _number(item.get("per")), _number(item.get("priceBV")), _number(item.get("evEbitda")),
                _number(item.get("dividendYield")), "idx",
            ))
        if not rows:
            return 0
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            execute_values(cursor, """
                INSERT INTO financial_ratios
                (ticker, fiscal_year, fiscal_period, period_end, revenue, cost_of_goods_sold,
                 gross_profit, operating_income, net_income, eps, total_assets, total_liabilities,
                 total_equity, cash_and_equivalents, total_debt, gross_margin, operating_margin,
                 net_margin, roe, roa, roic, debt_to_equity, current_ratio, interest_coverage,
                 pe_ratio, pb_ratio, ev_ebitda, dividend_yield, source)
                VALUES %s
                ON CONFLICT (ticker, fiscal_year, fiscal_period) DO UPDATE SET
                    period_end = EXCLUDED.period_end,
                    revenue = EXCLUDED.revenue,
                    operating_income = EXCLUDED.operating_income,
                    net_income = EXCLUDED.net_income,
                    eps = EXCLUDED.eps,
                    total_assets = EXCLUDED.total_assets,
                    total_liabilities = EXCLUDED.total_liabilities,
                    total_equity = EXCLUDED.total_equity,
                    net_margin = EXCLUDED.net_margin,
                    roe = EXCLUDED.roe,
                    roa = EXCLUDED.roa,
                    pe_ratio = EXCLUDED.pe_ratio,
                    pb_ratio = EXCLUDED.pb_ratio,
                    updated_at = CURRENT_TIMESTAMP
            """, rows)
        self.connection.commit()
        return len(rows)

    def insert_index_summaries(self, records: Iterable[dict[str, Any]]) -> int:
        """Upsert daily index summary records."""
        rows = []
        for item in records:
            code = item.get("IndexCode") or item.get("index_code")
            summary_date = _date(item.get("Date") or item.get("summary_date"))
            if not code or not summary_date:
                continue
            rows.append((
                code, summary_date, _number(item.get("Previous")), _number(item.get("Highest")),
                _number(item.get("Lowest")), _number(item.get("Close") or item.get("close_value")),
                _number(item.get("NumberOfStock")), _number(item.get("Change") or item.get("change_value")),
                _number(item.get("Volume")), _number(item.get("Value") or item.get("traded_value")),
                _number(item.get("Frequency")), _number(item.get("MarketCapital")), "idx",
            ))
        if not rows:
            return 0
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            execute_values(cursor, """
                INSERT INTO index_summaries
                (index_code, summary_date, previous, highest, lowest, close_value,
                 number_of_stocks, change_value, volume, traded_value, frequency, market_capital, source)
                VALUES %s
                ON CONFLICT (index_code, summary_date) DO UPDATE SET
                    previous = EXCLUDED.previous,
                    highest = EXCLUDED.highest,
                    lowest = EXCLUDED.lowest,
                    close_value = EXCLUDED.close_value,
                    number_of_stocks = EXCLUDED.number_of_stocks,
                    change_value = EXCLUDED.change_value,
                    volume = EXCLUDED.volume,
                    traded_value = EXCLUDED.traded_value,
                    frequency = EXCLUDED.frequency,
                    market_capital = EXCLUDED.market_capital
            """, rows)
        self.connection.commit()
        return len(rows)

    def upsert_stock_prices(self, records: Iterable[dict[str, Any]]) -> int:
        """Upsert daily OHLCV price records into stock_prices.

        Accepts records with either yfinance-style keys (Open/High/Low/Close/Volume)
        or normalized lowercase keys (open_price/high_price/low_price/close_price/volume).
        (ticker, trading_date) is the deduplication key.
        """
        rows = []
        for item in records:
            ticker = (
                item.get("ticker")
                or item.get("symbol")
                or item.get("Symbol")
            )
            trading_date = _date(item.get("trading_date") or item.get("date") or item.get("Date"))
            if not ticker or not trading_date:
                continue
            rows.append((
                str(ticker).upper(),
                trading_date,
                _number(item.get("open_price") or item.get("Open")),
                _number(item.get("high_price") or item.get("High")),
                _number(item.get("low_price") or item.get("Low")),
                _number(item.get("close_price") or item.get("Close")),
                _int(item.get("volume") or item.get("Volume")),
                item.get("source") or "yfinance",
            ))
        if not rows:
            return 0
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            # stock_prices.ticker references companies(ticker); insert minimal
            # placeholder company rows when missing so price ingestion never
            # fails on the FK. DO NOTHING keeps existing company details intact.
            tickers = sorted({row[0] for row in rows})
            execute_values(cursor, """
                INSERT INTO companies (ticker, name)
                VALUES %s
                ON CONFLICT (ticker) DO NOTHING
            """, [(ticker, ticker) for ticker in tickers])
            execute_values(cursor, """
                INSERT INTO stock_prices
                    (ticker, trading_date, open_price, high_price, low_price, close_price, volume, source)
                VALUES %s
                ON CONFLICT (ticker, trading_date) DO UPDATE SET
                    open_price = EXCLUDED.open_price,
                    high_price = EXCLUDED.high_price,
                    low_price = EXCLUDED.low_price,
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume,
                    source = EXCLUDED.source
            """, rows)
        self.connection.commit()
        return len(rows)

    def update_financial_enrichments(
        self,
        records: Iterable[dict[str, Any]],
    ) -> int:
        """Update enrichment fields for latest ratio rows.

        Enrichment values (e.g. from yfinance) fill in fields the IDX ratios
        source leaves empty: dividend_yield, current_ratio, payout_ratio, growth
        CAGRs (revenue_cagr, earnings_cagr), and the cash-flow/interest
        components (gross_profit, cash_and_equivalents, interest_expense,
        operating_cash_flow, capital_expenditures) that let the analysis engine
        derive gross margin, interest coverage, net debt/EBITDA and FCF margin.
        Only the tagged value columns are updated; other ratio data is kept.
        """
        rows = []
        for item in records:
            ticker = item.get("ticker") or item.get("symbol") or item.get("Symbol")
            if not ticker:
                continue
            dividend_yield = _number(item.get("dividend_yield") or item.get("dividendYield"))
            if dividend_yield is not None:
                # yfinance returns a fraction (0.12) for most tickers but some
                # IDX tickers already come back as a percent (18.10). Normalise
                # to a percent without double-scaling, and clamp to a sane band.
                if 0 < dividend_yield <= 1:
                    dividend_yield *= 100
                dividend_yield = min(dividend_yield, 100.0) if dividend_yield > 0 else dividend_yield
            rows.append((
                str(ticker).upper(),
                dividend_yield,
                _number(item.get("current_ratio") or item.get("currentRatio")),
                _number(item.get("payout_ratio") or item.get("payoutRatio")),
                _number(item.get("revenue_cagr")),
                _number(item.get("earnings_cagr")),
                _number(item.get("gross_profit") or item.get("grossProfit")),
                _number(item.get("cash_and_equivalents") or item.get("cash")),
                _number(item.get("interest_expense")),
                _number(item.get("operating_cash_flow")),
                _number(item.get("capital_expenditures")),
            ))
        if not rows:
            return 0
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            execute_values(cursor, """
                UPDATE financial_ratios fr
                SET dividend_yield = data.dividend_yield::numeric,
                    current_ratio = data.current_ratio::numeric,
                    payout_ratio = data.payout_ratio::numeric,
                    revenue_cagr = data.revenue_cagr::numeric,
                    earnings_cagr = data.earnings_cagr::numeric,
                    gross_profit = data.gross_profit::numeric,
                    cash_and_equivalents = data.cash_and_equivalents::numeric,
                    interest_expense = data.interest_expense::numeric,
                    operating_cash_flow = data.operating_cash_flow::numeric,
                    capital_expenditures = data.capital_expenditures::numeric,
                    updated_at = CURRENT_TIMESTAMP
                FROM (VALUES %s) AS data(ticker, dividend_yield, current_ratio,
                                         payout_ratio, revenue_cagr, earnings_cagr,
                                         gross_profit, cash_and_equivalents,
                                         interest_expense, operating_cash_flow,
                                         capital_expenditures)
                WHERE fr.ticker = data.ticker
                  AND fr.fiscal_year = (
                      SELECT MAX(fiscal_year) FROM financial_ratios f2
                      WHERE f2.ticker = fr.ticker
                  )
            """, rows)
        self.connection.commit()
        return len(rows)

    def insert_news(self, records: Iterable[dict[str, Any]]) -> int:
        """Insert scraped news records idempotently.

        Maps the IDX NewsAnnouncement/GetNewsSearch response fields into the
        normalized news_articles schema. news_code is the deduplication key.
        """
        rows = []
        skipped = 0
        for item in records:
            if not isinstance(item, dict):
                continue
            title = (
                item.get("NewsTitle")
                or item.get("newsTitle")
                or item.get("Title")
                or item.get("title")
                or item.get("Judul")
                or item.get("judul")
            )
            if not title:
                skipped += 1
                continue

            url = self._extract_news_url(item)
            news_code = (
                item.get("NewsCode")
                or item.get("newsCode")
                or item.get("news_code")
                or item.get("ItemId")
                or item.get("Id")
                or item.get("id")
                or item.get("Code")
                or item.get("code")
            )
            if not news_code and url:
                news_code = _stable_hash(url)
            if not news_code:
                news_code = _stable_hash(title)

            ticker = (
                item.get("Ticker")
                or item.get("ticker")
                or item.get("Symbol")
                or item.get("symbol")
                or item.get("KodeEmiten")
            )
            content = (
                item.get("NewsContent")
                or item.get("newsContent")
                or item.get("Content")
                or item.get("content")
                or item.get("Summary")
                or item.get("summary")
                or item.get("Description")
                or item.get("description")
                or item.get("Isi")
                or item.get("isi")
            )
            rows.append((
                str(news_code)[:100],
                str(ticker).upper() if ticker else None,
                str(title)[:500],
                str(content) if content else None,
                item.get("Source") or item.get("source")
                or item.get("NewsSource") or item.get("newsSource")
                or "IDX",
                _datetime(
                    item.get("PublishedAt")
                    or item.get("publishedAt")
                    or item.get("PublishedDate")
                    or item.get("published_date")
                    or item.get("NewsDate")
                    or item.get("newsDate")
                    or item.get("Date")
                    or item.get("date")
                ),
                url,
                item.get("ImageUrl") or item.get("imageUrl") or item.get("image_url") or item.get("Image"),
                _number(item.get("sentiment_score")),
            ))
        if skipped:
            print(f"Skipped {skipped} news records without a title.")
        if not rows:
            print("No news records with a title to insert.")
            return 0
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            execute_values(cursor, """
                INSERT INTO news_articles
                    (news_code, ticker, title, content, source, published_at, url, image_url, sentiment_score)
                VALUES %s
                ON CONFLICT (news_code) DO NOTHING
            """, rows)
        self.connection.commit()
        return len(rows)

    def get_favorites(self) -> list[str]:
        """Return favorite tickers ordered by their saved position."""
        self._ensure_connection()
        assert self.connection is not None
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT ticker FROM favorites ORDER BY position ASC, created_at ASC"
            )
            return [row[0] for row in cursor.fetchall()]

    def upsert_research_candidates(
        self,
        candidates: Iterable[dict[str, Any]],
        llm_interpretation: str = "",
    ) -> int:
        """Persist deterministic research candidates idempotently (Fase B5).

        One row per (candidate_date, sector, ticker, direction). Re-running the
        same day updates confidence/reason/LLM text instead of duplicating rows.
        Propagates the FK for sector-level rows (ticker IS NULL).
        """
        candidates = list(candidates)
        if not candidates:
            return 0
        today = date.today()
        # Ensure referenced company rows exist before inserting ticker candidates.
        self._ensure_companies(candidates)
        rows = [
            (
                today,
                c.get("sector") or "Unknown",
                (c.get("ticker") or "").upper() or None,
                c.get("direction") or "neutral",
                float(c.get("confidence") or 0.0),
                float(c.get("net_strength") or 0.0),
                c.get("reason") or "",
                llm_interpretation or "",
                json.dumps(c.get("source_impacts") or [], default=str),
                c.get("status") or "pending",
            )
            for c in candidates
        ]
        self._ensure_connection()
        assert self.connection is not None
        with self.connection.cursor() as cursor:
            execute_values(
                cursor,
                """
                INSERT INTO research_candidates
                    (candidate_date, sector, ticker, direction, confidence,
                     net_strength, reason, llm_interpretation, source_impacts, status)
                VALUES %s
                ON CONFLICT (candidate_date, sector, COALESCE(ticker, ''), direction)
                DO UPDATE SET
                    confidence = EXCLUDED.confidence,
                    net_strength = EXCLUDED.net_strength,
                    reason = EXCLUDED.reason,
                    llm_interpretation = COALESCE(NULLIF(EXCLUDED.llm_interpretation, ''), research_candidates.llm_interpretation),
                    source_impacts = EXCLUDED.source_impacts,
                    status = EXCLUDED.status,
                    batch_generated_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                """,
                rows,
            )
        self.connection.commit()
        return len(rows)

    def _ensure_companies(self, candidates: Iterable[dict[str, Any]]) -> None:
        """Insert placeholder company rows for any tickers referenced by candidates."""
        tickers = []
        for c in candidates:
            t = (c.get("ticker") or "").upper()
            if t and t not in tickers:
                tickers.append(t)
        if not tickers:
            return
        self._ensure_connection()
        assert self.connection is not None
        with self.connection.cursor() as cursor:
            execute_values(
                cursor,
                """
                INSERT INTO companies (ticker, name)
                VALUES %s
                ON CONFLICT (ticker) DO NOTHING
                """,
                [(t, t) for t in tickers],
            )

    def get_research_candidates(self, hours: int | None = None) -> list[dict[str, Any]]:
        """Return research candidates, optionally limited to the last ``hours``."""
        self._ensure_connection()
        assert self.connection is not None
        query = (
            "SELECT candidate_date, sector, ticker, direction, confidence, "
            "net_strength, reason, status, llm_interpretation "
            "FROM research_candidates "
        )
        params: tuple = ()
        if hours:
            query += "WHERE candidate_date >= CURRENT_DATE - CONCAT(%s, ' hours')::interval "
            params = (hours,)
        query += "ORDER BY candidate_date DESC, ABS(net_strength) DESC, sector ASC"
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def add_favorite(self, ticker: str) -> bool:
        """Add a ticker to favorites. Returns True when newly added, False if it already existed."""
        ticker = str(ticker).upper()
        self._ensure_connection()
        assert self.connection is not None
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO favorites (ticker, position)
                VALUES (%s, COALESCE((SELECT MAX(position) FROM favorites), 0) + 1)
                ON CONFLICT (ticker) DO NOTHING
                RETURNING ticker
                """,
                (ticker,),
            )
            row = cursor.fetchone()
        self.connection.commit()
        return bool(row and row[0])

    def remove_favorite(self, ticker: str) -> bool:
        """Remove a ticker from favorites. Returns True when a row was deleted."""
        self._ensure_connection()
        assert self.connection is not None
        with self.connection.cursor() as cursor:
            cursor.execute("DELETE FROM favorites WHERE ticker = %s", (str(ticker).upper(),))
            deleted = cursor.rowcount > 0
        self.connection.commit()
        return deleted

    def set_price_alert(self, ticker: str, alert_price: float, direction: str = "above") -> bool:
        """Set a price alert on a watchlist ticker (auto-adds it to favorites).

        ``direction`` is ``above`` (alert when close >= target) or ``below``.
        """
        self._ensure_connection()
        assert self.connection is not None
        if alert_price <= 0:
            raise ValueError("alert_price must be positive")
        direction = "below" if direction == "below" else "above"
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO favorites (ticker, position, alert_price, alert_direction, alert_enabled)
                VALUES (%s, COALESCE((SELECT MAX(position) FROM favorites), 0) + 1, %s, %s, true)
                ON CONFLICT (ticker)
                DO UPDATE SET alert_price = EXCLUDED.alert_price,
                              alert_direction = EXCLUDED.alert_direction,
                              alert_enabled = true,
                              alert_updated_at = CURRENT_TIMESTAMP
                RETURNING ticker
                """,
                (str(ticker).upper(), alert_price, direction),
            )
            row = cursor.fetchone()
        self.connection.commit()
        return bool(row and row[0])

    def remove_price_alert(self, ticker: str) -> bool:
        """Clear the price alert for a watchlist ticker."""
        self._ensure_connection()
        assert self.connection is not None
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE favorites SET alert_price = NULL, alert_enabled = false
                WHERE ticker = %s
                """,
                (str(ticker).upper(),),
            )
            updated = cursor.rowcount > 0
        self.connection.commit()
        return updated

    def get_favorites_details(self) -> list[dict[str, Any]]:
        """Return favorites with their alert config and latest close price."""
        self._ensure_connection()
        assert self.connection is not None
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT f.ticker, f.alert_price, f.alert_direction, f.alert_enabled,
                       sp.close_price, sp.trading_date
                FROM favorites f
                LEFT JOIN (
                    SELECT ticker, close_price, trading_date,
                           ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY trading_date DESC) AS rn
                    FROM stock_prices
                ) sp ON sp.ticker = f.ticker AND sp.rn = 1
                ORDER BY f.position ASC, f.created_at ASC
                """
            )
            rows = cursor.fetchall()
        details = []
        for ticker, alert_price, direction, enabled, close, as_of in rows:
            price = float(close) if close is not None else None
            target = float(alert_price) if alert_price is not None else None
            triggered = False
            if target and price is not None:
                triggered = (
                    price >= target if direction == "above" else price <= target
                )
            details.append({
                "ticker": ticker,
                "alert_price": target,
                "alert_direction": direction,
                "alert_enabled": bool(enabled),
                "current_price": price,
                "as_of": str(as_of) if as_of else None,
                "triggered": triggered,
            })
        return details

    def get_triggered_alerts(self) -> list[dict[str, Any]]:
        """Return active alerts whose price condition has been met."""
        return [
            d for d in self.get_favorites_details()
            if d["alert_enabled"] and d["alert_price"] is not None and d["triggered"]
        ]

    @staticmethod
    def _extract_news_url(item: dict[str, Any]) -> str | None:
        """Derive the news URL from the Links[].Href field."""
        links = item.get("Links")
        if isinstance(links, list):
            for link in links:
                if isinstance(link, dict):
                    href = link.get("Href")
                    if href:
                        return str(href)
        return item.get("Url") or item.get("url") or item.get("Link") or item.get("link")

    def _ensure_connection(self):
        if self.connection is None or self.connection.closed:
            self.connect()


def save_raw_json(path: str | Path, data: Any) -> None:
    """Save a raw scraper response only when explicitly enabled."""
    if os.getenv("SCRAPER_SAVE_JSON", "false").lower() != "true":
        return
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def _stable_hash(value: Any) -> str:
    """Return a deterministic short hash for a string (DEDUP-stable).

    Python's builtin ``hash`` is randomized per-process (PYTHONHASHSEED), so
    using it as a persisted dedup key would produce a different value on every
    run and silently duplicate records. SHA-1 is stable across processes and
    machines.
    """
    text = str(value or "").encode("utf-8", errors="ignore")
    return hashlib.sha1(text).hexdigest()


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    # Reject NaN / infinities so they never pollute numeric columns.
    if str(number).lower() in ("nan", "inf", "+inf", "-inf") or number != number:
        return None
    return number


def _int(value: Any) -> int | None:
    number = _number(value)
    return int(number) if number is not None else None


def _date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None


def _datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
