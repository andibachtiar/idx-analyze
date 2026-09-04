"""
Scraper for daily OHLCV stock prices via Yahoo Finance.

Fetches per-ticker daily price history and persists it to PostgreSQL
(stock_prices table) with idempotent upserts.

Flows:
    1. Single stock:    --ticker BBCA
    2. Date range:      --ticker BBCA --start 2025-01-01 --end 2025-12-31
    3. Daily (default): no --start/--end -> only fetches dates missing
       from the database (incremental update up to today).
    4. Backfill:        --backfill -> fetch ~5 years of history.

All tickers are resolved to yfinance format (BBCA -> BBCA.JK). Tickers
without a date range and without stored prices fall back to a default
lookback so they still get useful history.
"""

from __future__ import annotations

import argparse
import math
import time
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from database.scraper_store import ScraperDatabase
from yfinance_data import get_idx_tickers

DEFAULT_LOOKBACK_DAYS = 365 * 2  # used when no range given and no stored prices
BACKFILL_DAYS = 365 * 5
YF_PERIOD = "1d"


def normalize_yf_ticker(ticker: str) -> str:
    """Convert an IDX ticker (BBCA) to yfinance format (BBCA.JK)."""
    ticker = ticker.strip().upper()
    if ticker.endswith(".JK"):
        return ticker
    return f"{ticker}.JK"


def to_idx_ticker(yf_ticker: str) -> str:
    """Strip the .JK suffix to get the IDX ticker used in PostgreSQL."""
    ticker = yf_ticker.upper()
    if ticker.endswith(".JK"):
        return ticker.removesuffix(".JK")
    return ticker


def resolve_range(
    start: str | None,
    end: str | None,
    existing_dates: set[date] | None = None,
    today: date | None = None,
) -> tuple[date, date]:
    """Resolve the fetch range for a ticker.

    - Explicit --start/--end win.
    - Otherwise daily mode: fetch only missing dates. When the database has
      stored prices, the range starts the day after the latest stored date.
      When nothing is stored, fall back to DEFAULT_LOOKBACK_DAYS.
    - An explicit --start with no --end defaults to today.
    """
    today = today or date.today()
    if start:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end) if end else today
        return start_date, end_date

    if end:
        raise ValueError("--end requires --start")

    if existing_dates:
        # Incremental: fetch everything after the newest stored row.
        latest = max(existing_dates)
        start_date = latest + timedelta(days=1)
        end_date = today
    else:
        start_date = today - timedelta(days=DEFAULT_LOOKBACK_DAYS)
        end_date = today
    return start_date, end_date


def fetch_prices(yf_ticker: str, start_date: date, end_date: date) -> list[dict]:
    """Fetch daily OHLCV rows for one yfinance ticker."""
    if start_date > end_date:
        return []

    data = yf.download(
        yf_ticker,
        start=start_date.isoformat(),
        end=(end_date + timedelta(days=1)).isoformat(),  # yfinance end is exclusive
        interval=YF_PERIOD,
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    if data is None or data.empty:
        return []

    if isinstance(data.columns, pd.MultiIndex):
        # MultiIndex columns: [('Open', 'BBCA.JK'), ...] -> flatten to single level.
        data.columns = data.columns.get_level_values(0)

    ticker = to_idx_ticker(yf_ticker)
    records = []
    for index, row in data.iterrows():
        trading_date = pd.Timestamp(index).date()
        close = _clean(row.get("Close"))
        if close is None:
            continue  # skip non-trading days / empty rows
        records.append({
            "ticker": ticker,
            "date": trading_date.isoformat(),
            "open_price": _clean(row.get("Open")),
            "high_price": _clean(row.get("High")),
            "low_price": _clean(row.get("Low")),
            "close_price": close,
            "volume": _clean_int(row.get("Volume")),
            "source": "yfinance",
        })
    return records


def _clean(value) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
        return None if math.isnan(number) else number
    except (TypeError, ValueError):
        return None


def _clean_int(value) -> int | None:
    number = _clean(value)
    return int(number) if number is not None else None


def stored_dates(store: ScraperDatabase, ticker: str) -> set[date]:
    """Return the set of trading dates already stored for a ticker."""
    store._ensure_connection()
    assert store.connection is not None
    with store.connection.cursor() as cursor:
        cursor.execute(
            "SELECT trading_date FROM stock_prices WHERE ticker = %s",
            (ticker.upper(),),
        )
        return {row[0] for row in cursor.fetchall()}


def scrape_ticker_prices(
    store: ScraperDatabase,
    ticker: str,
    start: str | None = None,
    end: str | None = None,
    backfill: bool = False,
) -> tuple[int, int]:
    """Scrape prices for a single ticker and persist them.

    Returns (fetched_rows, persisted_rows).
    """
    yf_ticker = normalize_yf_ticker(ticker)
    existing = stored_dates(store, to_idx_ticker(ticker))

    if backfill:
        start_date = date.today() - timedelta(days=BACKFILL_DAYS)
        end_date = date.today()
    else:
        start_date, end_date = resolve_range(start, end, existing or None)

    print(f"[{to_idx_ticker(ticker)}] range {start_date} -> {end_date} "
          f"({len(existing)} rows already stored)")

    records = fetch_prices(yf_ticker, start_date, end_date)
    if not records:
        print(f"[{to_idx_ticker(ticker)}] no new price rows to persist")
        return 0, 0

    persisted = store.upsert_stock_prices(records)
    print(f"[{to_idx_ticker(ticker)}] fetched {len(records)} rows, persisted {persisted}")
    return len(records), persisted


def get_company_tickers(store: ScraperDatabase) -> list[str]:
    """Return all tickers from the companies table (the IDX universe)."""
    store._ensure_connection()
    assert store.connection is not None
    with store.connection.cursor() as cursor:
        cursor.execute("SELECT ticker FROM companies ORDER BY ticker")
        return [row[0] for row in cursor.fetchall()]


def scrape_prices(
    tickers: list[str] | None = None,
    start: str | None = None,
    end: str | None = None,
    backfill: bool = False,
    delay_seconds: float = 0.5,
) -> int:
    """Scrape prices for multiple tickers and persist to PostgreSQL.

    When no explicit tickers are given, the full universe is read from the
    companies table; the sample list in yfinance_data is used only as a
    fallback when the table is empty.
    """
    total = 0
    with ScraperDatabase() as store:
        targets = tickers
        if targets is None:
            targets = get_company_tickers(store)
            if not targets:
                targets = get_idx_tickers()
                print(f"Companies table is empty; falling back to {len(targets)} sample tickers. "
                      "Run scrape_company_profiles.py to populate the full IDX universe.")
        print(f"Scraping {len(targets)} tickers...")
        for index, ticker in enumerate(targets, start=1):
            print(f"[{index}/{len(targets)}] {ticker}")
            _, persisted = scrape_ticker_prices(store, ticker, start, end, backfill)
            total += persisted
            if delay_seconds:
                time.sleep(delay_seconds)
    return total


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape daily OHLCV stock prices into PostgreSQL",
    )
    parser.add_argument(
        "--ticker",
        action="append",
        help="IDX ticker to scrape (repeatable, e.g. --ticker BBCA --ticker TLKM)",
    )
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD, requires --start)")
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Fetch ~5 years of history regardless of stored data",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Seconds to wait between tickers (default: 0.5)",
    )
    args = parser.parse_args()

    if args.end and not args.start:
        parser.error("--end requires --start")

    persisted = scrape_prices(
        tickers=args.ticker,
        start=args.start,
        end=args.end,
        backfill=args.backfill,
        delay_seconds=args.delay,
    )
    print(f"Done. Persisted {persisted} stock price rows to PostgreSQL.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
