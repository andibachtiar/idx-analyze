"""
Scraper for company-specific news via Yahoo Finance.

Fetches per-ticker news using yFinance's stock.news and persists it to
PostgreSQL with the ticker populated, so the research/events pipeline can
link each article to a company.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

import yfinance as yf

from database.scraper_store import ScraperDatabase


def fetch_ticker_news(yfinance_ticker: str) -> list:
    """Return normalized news records for a single yfinance ticker."""
    try:
        stock = yf.Ticker(yfinance_ticker)
        items = stock.news or []
    except Exception as exc:  # pragma: no cover - network variance
        print(f"  Failed to fetch news for {yfinance_ticker}: {exc}")
        return []

    # Normalize and attach the resolved IDX ticker (without the .JK suffix).
    ticker = yfinance_ticker.upper()
    if ticker.endswith(".JK"):
        ticker = ticker.removesuffix(".JK")

    records = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        url = item.get("link")
        if not title or not url:
            continue

        published = item.get("providerPublishTime")
        published_dt = None
        if published:
            try:
                published_dt = datetime.fromtimestamp(int(published), tz=UTC)
            except (TypeError, ValueError):
                published_dt = None

        records.append({
            "ticker": ticker,
            "title": title,
            "url": url,
            "source": item.get("publisher") or "Yahoo Finance",
            "publishedAt": published_dt.isoformat() if published_dt else None,
            # Deterministic dedup key derived from the URL.
            "newsCode": f"{ticker}-{abs(hash(url))}",
            "itemType": item.get("type"),
        })
    return records


def get_company_tickers() -> list[str]:
    """Read all tickers from the companies table (IDX universe)."""
    with ScraperDatabase() as store:
        store._ensure_connection()
        assert store.connection is not None
        with store.connection.cursor() as cursor:
            cursor.execute("SELECT ticker FROM companies ORDER BY ticker")
            return [row[0] for row in cursor.fetchall()]


def scrape_company_news(
    tickers: list | None = None,
    delay_seconds: float = 0.2,
    limit: int | None = None,
    offset: int = 0,
) -> int:
    """Fetch company news for the given tickers and persist to PostgreSQL."""
    if tickers is None:
        tickers = get_company_tickers()
    tickers = tickers[offset:]
    if limit:
        tickers = tickers[:limit]
    # yfinance expects the .JK suffix for IDX tickers.
    yfinance_tickers = [
        t.upper() if t.upper().endswith(".JK") else f"{t}.JK" for t in tickers
    ]
    print(f"Fetching company news for {len(yfinance_tickers)} tickers...")

    all_records = []
    for index, yticker in enumerate(yfinance_tickers, start=1):
        print(f"[{index}/{len(yfinance_tickers)}] {yticker}")
        records = fetch_ticker_news(yticker)
        all_records.extend(records)
        print(f"  -> {len(records)} news records")
        if delay_seconds:
            time.sleep(delay_seconds)

    if not all_records:
        print("No company news was collected.")
        return 0

    try:
        with ScraperDatabase() as store:
            imported = store.insert_news(all_records)
        print(f"Persisted {imported} company news records to PostgreSQL")
        return imported
    except Exception as exc:
        print(f"PostgreSQL persistence failed: {exc}")
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape per-ticker news from Yahoo Finance")
    parser.add_argument("--ticker", action="append", help="Specific ticker (repeatable)")
    parser.add_argument("--limit", type=int, help="Limit number of tickers")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N tickers")
    parser.add_argument("--delay", type=float, default=0.2, help="Delay between tickers")
    args = parser.parse_args()

    scrape_company_news(
        tickers=args.ticker,
        delay_seconds=args.delay,
        limit=args.limit,
        offset=args.offset,
    )
