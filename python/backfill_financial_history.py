"""
Backfill multi-year financial history into ``financial_ratios`` for each ticker.

The IDX ratio scrape only stores a single "latest" row per ticker, so the
fundamentals chart would show a single point. This script pulls the multi-year
annual statements from yfinance (already available via ``Ticker.financials`` /
``Ticker.balance_sheet``) and upserts one row per fiscal year that is not
already present, computing margins deterministically.

Usage:
    uv run python backfill_financial_history.py                    # all tickers
    uv run python backfill_financial_history.py --ticker BBRI     # one ticker
    uv run python backfill_financial_history.py --ticker BBCA --ticker BBRI
    uv run python backfill_financial_history.py --limit 50
"""

from __future__ import annotations

import argparse
import math
import time

import yfinance as yf

from database.scraper_store import ScraperDatabase


def normalize_yf_ticker(ticker: str) -> str:
    ticker = ticker.strip().upper()
    return ticker if ticker.endswith(".JK") else f"{ticker}.JK"


def to_idx_ticker(yf_ticker: str) -> str:
    ticker = yf_ticker.strip().upper()
    return ticker.removesuffix(".JK") if ticker.endswith(".JK") else ticker


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(num) or math.isinf(num) else num


def _row_series(frame, name: str) -> dict:
    """Return {period_end: float} for a financial-statement row, or {}."""
    if frame is None or name not in frame.index:
        return {}
    try:
        series = frame.loc[name]
    except Exception:
        return {}
    out = {}
    for period, value in series.items():
        num = _safe_float(value)
        if num is not None:
            out[period] = num
    return out


def to_idx_units(value: float | None) -> float | None:
    """Convert a raw rupiah (or band) monetary value to IDX billing convention.

    IDX financial ratios store monetary figures in IDR billions (e.g. BBRI
    2024 revenue ≈ 172124.02), while yfinance exposes raw IDR. We divide by
    1e9 to keep the same convention across all rows in ``financial_ratios``.
    """
    if value is None:
        return None
    return value / 1_000_000_000.0


def to_idx_pct(value: float | None) -> float | None:
    """Convert a fraction margin (e.g. 0.3327) to the IDX percentage (33.27)."""
    if value is None:
        return None
    return value * 100.0


def fetch_yf_history(yf_ticker: str) -> list[dict]:
    """Return per-period records from yfinance annual statements, newest-first.

    Each record uses the same keys expected by ``upsert_financial_ratios`` so it
    can be inserted directly (``code``, ``fsDate``, ``fiscalYear``, ``sales``,
    ``grossMargin``, ``operatingMargin``, ``npm``, ``profitAttrOwner``, ``ebt``,
    ``eps``, ``assets``, ``equity``, ``debt``).
    """
    try:
        ticker = yf.Ticker(yf_ticker)
        income = ticker.financials
        balance = ticker.balance_sheet
    except Exception as exc:  # pragma: no cover - network variance
        print(f"  Fetch failed for {yf_ticker}: {exc}")
        return []

    revenue = _row_series(income, "Total Revenue")
    net_income = _row_series(income, "Net Income")
    oper_income = _row_series(income, "Operating Income")
    eps = _row_series(income, "Diluted EPS")
    assets = _row_series(balance, "Total Assets")
    equity = _row_series(balance, "Stockholders Equity")
    debt = _row_series(balance, "Total Debt")

    if not revenue:
        return []

    periods = sorted(revenue.keys(), reverse=True)  # newest -> oldest
    records = []
    for period in periods:
        rev = revenue.get(period)
        ni = net_income.get(period)
        oi = oper_income.get(period)
        if rev is None:
            continue
        period_end = period if hasattr(period, "year") else None
        records.append({
            "code": to_idx_ticker(yf_ticker),
            "fsDate": period_end,
            "fiscalYear": getattr(period_end, "year", None),
            "sales": to_idx_units(rev),
            "grossMargin": None,
            "operatingMargin": to_idx_pct((oi / rev) if (oi is not None and rev) else None),
            "npm": to_idx_pct((ni / rev) if (ni is not None and rev) else None),
            "profitAttrOwner": to_idx_units(ni),
            "ebt": to_idx_units(oi),
            "eps": eps.get(period),
            "assets": to_idx_units(assets.get(period)),
            "equity": to_idx_units(equity.get(period)),
            "debt": to_idx_units(debt.get(period)),
        })
    return records


def _existing_years(store: ScraperDatabase, ticker: str) -> set[int]:
    store._ensure_connection()
    assert store.connection is not None
    with store.connection.cursor() as cursor:
        cursor.execute(
            "SELECT DISTINCT fiscal_year FROM financial_ratios WHERE ticker = %s",
            (ticker.upper(),),
        )
        return {row[0] for row in cursor.fetchall() if row[0] is not None}


def backfill_history(
    tickers: list[str] | None = None,
    limit: int | None = None,
    offset: int = 0,
    delay_seconds: float = 0.3,
) -> int:
    """Backfill multi-year financial history and persist to PostgreSQL."""
    if tickers is None:
        with ScraperDatabase() as store:
            store._ensure_connection()
            assert store.connection is not None
            with store.connection.cursor() as cursor:
                cursor.execute("SELECT ticker FROM companies ORDER BY ticker")
                tickers = [row[0] for row in cursor.fetchall()]

    tickers = tickers[offset:]
    if limit:
        tickers = tickers[:limit]

    print(f"Backfilling financial history for {len(tickers)} tickers...")
    updated = 0
    with ScraperDatabase() as store:
        for index, ticker in enumerate(tickers, start=1):
            print(f"[{index}/{len(tickers)}] {ticker}")
            existing = _existing_years(store, ticker)
            records = fetch_yf_history(normalize_yf_ticker(ticker))
            missing = [r for r in records if r.get("fiscalYear") not in existing]
            if not missing:
                print("  -> no new history to add")
                continue
            count = store.upsert_financial_ratios(missing)
            inserted = [r["fiscalYear"] for r in missing]
            print(f"  -> inserted {count} row(s): {inserted}")
            updated += count
            if delay_seconds:
                time.sleep(delay_seconds)
    print(f"Done. Backfilled {updated} rows.")
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill multi-year financial history")
    parser.add_argument("--ticker", action="append", help="Specific ticker (repeatable)")
    parser.add_argument("--limit", type=int, help="Limit number of tickers (for testing)")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N tickers (for batching)")
    parser.add_argument("--delay", type=float, default=0.3, help="Delay between tickers (seconds)")
    args = parser.parse_args()

    backfill_history(
        tickers=args.ticker,
        limit=args.limit,
        offset=args.offset,
        delay_seconds=args.delay,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
