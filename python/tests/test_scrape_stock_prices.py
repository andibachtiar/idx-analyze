"""
Tests for the daily stock price scraper and its PostgreSQL store.

Covers:
- Ticker conversion (IDX <-> yfinance)
- Date range resolution (explicit range, daily/incremental mode, backfill)
- OHLCV value cleaning
- yfinance download normalization
- Scraper orchestration against a fake store
- Idempotent upsert SQL construction (upsert_stock_prices)
"""

from __future__ import annotations

import os
import sys
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.scraper_store import ScraperDatabase
from scrape_stock_prices import (
    DEFAULT_LOOKBACK_DAYS,
    _clean,
    _clean_int,
    fetch_prices,
    get_company_tickers,
    normalize_yf_ticker,
    resolve_range,
    scrape_prices,
    scrape_ticker_prices,
    stored_dates,
    to_idx_ticker,
)

# =============================================================================
# TICKER CONVERSION
# =============================================================================

class TestTickerConversion:
    def test_normalize_yf_ticker_adds_jk(self):
        assert normalize_yf_ticker("BBCA") == "BBCA.JK"

    def test_normalize_yf_ticker_preserves_jk(self):
        assert normalize_yf_ticker("BBCA.JK") == "BBCA.JK"

    def test_normalize_yf_ticker_lowercase(self):
        assert normalize_yf_ticker("bbca") == "BBCA.JK"

    def test_to_idx_ticker_strips_jk(self):
        assert to_idx_ticker("BBCA.JK") == "BBCA"

    def test_to_idx_ticker_keeps_plain(self):
        assert to_idx_ticker("BBCA") == "BBCA"


# =============================================================================
# DATE RANGE RESOLUTION
# =============================================================================

class TestResolveRange:
    def test_explicit_start_and_end(self):
        start, end = resolve_range("2025-01-01", "2025-06-30", today=date(2025, 12, 31))
        assert start == date(2025, 1, 1)
        assert end == date(2025, 6, 30)

    def test_explicit_start_only_defaults_end_to_today(self):
        start, end = resolve_range("2025-01-01", None, today=date(2025, 12, 31))
        assert start == date(2025, 1, 1)
        assert end == date(2025, 12, 31)

    def test_daily_mode_continues_after_latest_stored(self):
        existing = {date(2025, 1, 1), date(2025, 3, 15)}
        start, end = resolve_range(None, None, existing, today=date(2025, 12, 31))
        assert start == date(2025, 3, 16)
        assert end == date(2025, 12, 31)

    def test_daily_mode_falls_back_when_no_data(self):
        start, end = resolve_range(None, None, None, today=date(2025, 12, 31))
        assert start == date(2025, 12, 31) - __import__("datetime").timedelta(days=DEFAULT_LOOKBACK_DAYS)
        assert end == date(2025, 12, 31)

    def test_end_without_start_raises(self):
        with pytest.raises(ValueError):
            resolve_range(None, "2025-06-30")


# =============================================================================
# VALUE CLEANING
# =============================================================================

class TestCleaning:
    def test_clean_number(self):
        assert _clean(1000) == 1000.0
        assert _clean("250.5") == 250.5

    def test_clean_none(self):
        assert _clean(None) is None

    def test_clean_nan(self):
        assert _clean(float("nan")) is None

    def test_clean_invalid(self):
        assert _clean("abc") is None

    def test_clean_int(self):
        assert _clean_int(1000) == 1000
        assert _clean_int(None) is None
        assert _clean_int("250.9") == 250


# =============================================================================
# YFINANCE FETCH / NORMALIZATION
# =============================================================================

def _fake_download_frame(close_nan: bool = False) -> pd.DataFrame:
    """Build a DataFrame shaped like a yfinance download with single-level columns."""
    index = pd.to_datetime(["2025-01-02", "2025-01-03"])
    close = [100.0, float("nan")] if close_nan else [100.0, 105.0]
    return pd.DataFrame(
        {
            "Open": [99.0, 101.0],
            "High": [102.0, 106.0],
            "Low": [98.0, 100.0],
            "Close": close,
            "Volume": [1000000, 1200000],
        },
        index=index,
    )


class TestFetchPrices:
    @patch("scrape_stock_prices.yf.download")
    def test_fetch_prices_basic(self, mock_download):
        mock_download.return_value = _fake_download_frame()
        records = fetch_prices("BBCA.JK", date(2025, 1, 1), date(2025, 1, 10))

        assert len(records) == 2
        first = records[0]
        assert first["ticker"] == "BBCA"
        assert first["date"] == "2025-01-02"
        assert first["close_price"] == 100.0
        assert first["open_price"] == 99.0
        assert first["volume"] == 1000000
        assert first["source"] == "yfinance"

        # yfinance end date is exclusive -> +1 day passed through
        call_args = mock_download.call_args
        assert call_args.kwargs["start"] == "2025-01-01"
        assert call_args.kwargs["end"] == "2025-01-11"
        assert call_args.kwargs["interval"] == "1d"

    @patch("scrape_stock_prices.yf.download")
    def test_fetch_prices_skips_nan_close(self, mock_download):
        mock_download.return_value = _fake_download_frame(close_nan=True)
        records = fetch_prices("BBCA.JK", date(2025, 1, 1), date(2025, 1, 10))
        assert len(records) == 1
        assert records[0]["date"] == "2025-01-02"

    @patch("scrape_stock_prices.yf.download")
    def test_fetch_prices_empty(self, mock_download):
        mock_download.return_value = pd.DataFrame()
        assert fetch_prices("BBCA.JK", date(2025, 1, 1), date(2025, 1, 10)) == []

    def test_fetch_prices_start_after_end(self):
        assert fetch_prices("BBCA.JK", date(2025, 6, 1), date(2025, 1, 1)) == []

    @patch("scrape_stock_prices.yf.download")
    def test_fetch_prices_multiindex_columns(self, mock_download):
        """yfinance returns MultiIndex columns when multiple tickers downloaded."""
        inner = pd.DataFrame(
            {
                ("Open", "BBCA.JK"): [99.0],
                ("High", "BBCA.JK"): [102.0],
                ("Low", "BBCA.JK"): [98.0],
                ("Close", "BBCA.JK"): [100.0],
                ("Volume", "BBCA.JK"): [500000],
            },
            index=pd.to_datetime(["2025-01-02"]),
        )
        inner.columns = pd.MultiIndex.from_tuples(inner.columns)
        mock_download.return_value = inner
        records = fetch_prices("BBCA.JK", date(2025, 1, 1), date(2025, 1, 10))
        assert len(records) == 1
        assert records[0]["close_price"] == 100.0


# =============================================================================
# SCRAPER ORCHESTRATION (with a fake store)
# =============================================================================

class FakeStore:
    """Minimal stand-in for ScraperDatabase persistence methods."""

    def __init__(
        self,
        existing: set[date] | None = None,
        tickers: list[str] | None = None,
    ):
        self.existing = existing or set()
        self.upserted: list[list[dict]] = []
        self.connection = FakeConnection(self.existing, tickers or [])

    def _ensure_connection(self):
        pass

    def upsert_stock_prices(self, records):
        records = list(records)
        self.upserted.append(records)
        return len(records)


class FakeCursor:
    def __init__(self, dates, tickers=None, connection=None):
        self.dates = dates
        self.tickers = tickers or []
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def execute(self, query, params=None):
        pass

    def fetchall(self):
        if self.tickers:
            return [(t,) for t in self.tickers]
        return [(d,) for d in self.dates]


class FakeConnection:
    def __init__(self, dates, tickers=None):
        self.encoding = "UTF8"
        self.closed = False
        self._cursor = FakeCursor(dates, tickers, connection=self)

    def cursor(self):
        return self._cursor


class TestStoredDates:
    def test_stored_dates_returns_set(self):
        store = MagicMock()
        store.connection = FakeConnection({date(2025, 1, 2), date(2025, 1, 3)})
        result = stored_dates(store, "BBCA")
        assert result == {date(2025, 1, 2), date(2025, 1, 3)}


class TestScrapeTickerPrices:
    @patch("scrape_stock_prices.fetch_prices")
    def test_scrape_persists_and_returns_counts(self, mock_fetch):
        store = FakeStore(existing={date(2025, 1, 2)})
        mock_fetch.return_value = [
            {"ticker": "BBCA", "date": "2025-01-03", "close_price": 100.0},
            {"ticker": "BBCA", "date": "2025-01-04", "close_price": 101.0},
        ]
        fetched, persisted = scrape_ticker_prices(store, "BBCA", start="2025-01-03", end="2025-01-05")
        assert fetched == 2
        assert persisted == 2
        assert store.upserted[0][0]["ticker"] == "BBCA"

    @patch("scrape_stock_prices.fetch_prices")
    def test_scrape_no_records_returns_zeros(self, mock_fetch):
        store = FakeStore()
        mock_fetch.return_value = []
        fetched, persisted = scrape_ticker_prices(store, "BBCA")
        assert fetched == 0
        assert persisted == 0
        assert store.upserted == []

    @patch("scrape_stock_prices.fetch_prices")
    def test_scrape_backfill_uses_wide_range(self, mock_fetch):
        store = FakeStore()
        mock_fetch.return_value = [{"ticker": "BBCA", "date": "2025-01-02", "close_price": 100.0}]
        _, persisted = scrape_ticker_prices(store, "BBCA", backfill=True)
        assert persisted == 1
        start_arg = mock_fetch.call_args.args[1]
        end_arg = mock_fetch.call_args.args[2]
        assert (date.today() - start_arg).days >= 365 * 4
        assert end_arg == date.today()


class TestGetCompanyTickers:
    def test_returns_tickers_from_companies_table(self):
        store = FakeStore(tickers=["BBCA", "BBRI", "TLKM"])
        assert get_company_tickers(store) == ["BBCA", "BBRI", "TLKM"]

    def test_returns_empty_list_when_no_companies(self):
        store = FakeStore()
        assert get_company_tickers(store) == []


class TestScrapePrices:
    @patch("scrape_stock_prices.scrape_ticker_prices")
    def test_uses_companies_table_when_no_explicit_tickers(self, mock_scrape):
        mock_scrape.return_value = (1, 1)
        with patch("scrape_stock_prices.ScraperDatabase") as mock_db:
            mock_db.return_value.__enter__.return_value = FakeStore(tickers=["BBCA", "BBRI"])
            total = scrape_prices()
        assert total == 2
        called_tickers = [call.args[1] for call in mock_scrape.call_args_list]
        assert called_tickers == ["BBCA", "BBRI"]

    @patch("scrape_stock_prices.scrape_ticker_prices")
    def test_falls_back_to_sample_tickers_when_table_empty(self, mock_scrape):
        mock_scrape.return_value = (1, 1)
        with patch("scrape_stock_prices.ScraperDatabase") as mock_db:
            mock_db.return_value.__enter__.return_value = FakeStore()  # no companies
            with patch("scrape_stock_prices.get_idx_tickers") as mock_sample:
                mock_sample.return_value = ["BBCA.JK", "BBRI.JK"]
                total = scrape_prices()
        assert total == 2
        mock_sample.assert_called_once()
        called_tickers = [call.args[1] for call in mock_scrape.call_args_list]
        assert called_tickers == ["BBCA.JK", "BBRI.JK"]

    @patch("scrape_stock_prices.scrape_ticker_prices")
    def test_explicit_tickers_skip_database(self, mock_scrape):
        mock_scrape.return_value = (1, 1)
        with patch("scrape_stock_prices.ScraperDatabase") as mock_db:
            mock_db.return_value.__enter__.return_value = FakeStore(tickers=["BBCA"])
            total = scrape_prices(tickers=["TLKM"])
        assert total == 1
        called_tickers = [call.args[1] for call in mock_scrape.call_args_list]
        assert called_tickers == ["TLKM"]


# =============================================================================
# UPSERT SQL (against a fake psycopg2 cursor)
# =============================================================================

def _make_store_with_fake_connection():
    store = ScraperDatabase(database_url="postgresql://fake")
    fake_cursor = MagicMock()

    def _mogrify(template: bytes, args) -> bytes:
        # Mimic psycopg2: render the VALUES tuple with the row's values.
        rendered = ", ".join(repr(a) for a in args)
        return b"(" + rendered.encode() + b")"

    fake_cursor.mogrify.side_effect = _mogrify
    fake_connection = MagicMock()
    fake_connection.encoding = "UTF8"
    fake_connection.closed = False
    # The store uses `with self.connection.cursor() as cursor`; make the
    # context manager yield our fake cursor whose .connection is the fake.
    fake_connection.cursor.return_value.__enter__.return_value = fake_cursor
    fake_cursor.connection = fake_connection
    store.connection = fake_connection
    return store, fake_cursor


def _executed_statements(fake_cursor) -> list[str]:
    """Return all SQL statements passed to cursor.execute as decoded strings."""
    statements = []
    for call in fake_cursor.execute.call_args_list:
        sql = call[0][0]
        if isinstance(sql, bytes):
            statements.append(sql.decode("utf-8"))
    return statements


class TestUpsertStockPrices:
    def test_upsert_maps_yfinance_keys(self):
        store, fake_cursor = _make_store_with_fake_connection()
        records = [
            {
                "ticker": "BBCA",
                "date": "2025-01-02",
                "Open": 99.0,
                "High": 102.0,
                "Low": 98.0,
                "Close": 100.0,
                "Volume": 1000000,
            }
        ]
        count = store.upsert_stock_prices(records)
        assert count == 1
        statements = _executed_statements(fake_cursor)
        price_sql = next(s for s in statements if "INSERT INTO stock_prices" in s)
        assert "ON CONFLICT (ticker, trading_date) DO UPDATE" in price_sql
        assert "'BBCA'" in price_sql
        # The date column is normalized to a datetime.date object (mock repr).
        assert "datetime.date(2025, 1, 2)" in price_sql
        assert "100.0" in price_sql
        assert "1000000" in price_sql

    def test_upsert_ensures_company_row_exists(self):
        """Missing companies are created as placeholders (FK safety)."""
        store, fake_cursor = _make_store_with_fake_connection()
        records = [
            {"ticker": "BBRI", "date": "2025-01-02", "Close": 100.0},
            {"ticker": "BBCA", "date": "2025-01-02", "Close": 200.0},
        ]
        count = store.upsert_stock_prices(records)
        assert count == 2
        statements = _executed_statements(fake_cursor)
        company_sql = statements[0]
        assert "INSERT INTO companies" in company_sql
        assert "ON CONFLICT (ticker) DO NOTHING" in company_sql
        # Both tickers get placeholder rows, uppercased and de-duplicated.
        assert "('BBRI', 'BBRI')" in company_sql
        assert "('BBCA', 'BBCA')" in company_sql

    def test_upsert_maps_normalized_keys(self):
        store, fake_cursor = _make_store_with_fake_connection()
        records = [
            {
                "ticker": "bbca",
                "trading_date": "2025-01-02",
                "open_price": 99.0,
                "high_price": 102.0,
                "low_price": 98.0,
                "close_price": 100.0,
                "volume": "1000000",
                "source": "idx",
            }
        ]
        count = store.upsert_stock_prices(records)
        assert count == 1
        statements = _executed_statements(fake_cursor)
        price_sql = next(s for s in statements if "INSERT INTO stock_prices" in s)
        # ticker uppercased inside the generated statement
        assert "'BBCA'" in price_sql
        assert "'idx'" in price_sql

    def test_upsert_skips_missing_ticker_or_date(self):
        store, _ = _make_store_with_fake_connection()
        assert store.upsert_stock_prices([{"ticker": "BBCA"}]) == 0
        assert store.upsert_stock_prices([{"date": "2025-01-02"}]) == 0
        assert store.upsert_stock_prices([]) == 0

    def test_upsert_handles_iso_datetime_date(self):
        store, fake_cursor = _make_store_with_fake_connection()
        records = [
            {
                "ticker": "BBCA",
                "date": "2025-01-02T00:00:00+00:00",
                "Close": 100.0,
            }
        ]
        count = store.upsert_stock_prices(records)
        assert count == 1
        statements = _executed_statements(fake_cursor)
        price_sql = next(s for s in statements if "INSERT INTO stock_prices" in s)
        assert "'BBCA'" in price_sql
        assert "datetime.date(2025, 1, 2)" in price_sql


class TestUpdateFinancialEnrichments:
    """Tests for update_financial_enrichments (dividend/current-ratio backfill)."""

    def test_updates_latest_row_only(self):
        store, fake_cursor = _make_store_with_fake_connection()
        count = store.update_financial_enrichments(
            [{"ticker": "BBCA", "dividend_yield": 0.03, "current_ratio": 1.5, "payout_ratio": 0.8,
              "revenue_cagr": 0.10, "earnings_cagr": 0.12}]
        )
        assert count == 1
        statements = _executed_statements(fake_cursor)
        update_sql = next(s for s in statements if "UPDATE financial_ratios" in s)
        assert "dividend_yield = data.dividend_yield::numeric" in update_sql
        assert "revenue_cagr = data.revenue_cagr::numeric" in update_sql
        assert "earnings_cagr = data.earnings_cagr::numeric" in update_sql
        # dividend_yield is converted to percent (0.03 -> 3)
        assert "3.0" in update_sql
        assert "1.5" in update_sql
        assert "0.8" in update_sql
        assert "0.1" in update_sql  # revenue_cagr kept as decimal
        assert "0.12" in update_sql

    def test_skips_missing_ticker(self):
        store, _ = _make_store_with_fake_connection()
        assert store.update_financial_enrichments(
            [{"dividend_yield": 0.03, "current_ratio": 1.5}]
        ) == 0

    def test_accepts_alternate_yfinance_keys(self):
        store, fake_cursor = _make_store_with_fake_connection()
        count = store.update_financial_enrichments(
            [{"Symbol": "BBRI", "dividendYield": 0.12, "currentRatio": 2.0, "payoutRatio": 0.9}]
        )
        assert count == 1
        statements = _executed_statements(fake_cursor)
        update_sql = next(s for s in statements if "UPDATE financial_ratios" in s)
        assert "'BBRI'" in update_sql
        assert "12.0" in update_sql  # 0.12 -> 12
        assert "2.0" in update_sql
        assert "0.9" in update_sql
