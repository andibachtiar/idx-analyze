"""
Scraper for yfinance enrichment fields (dividend_yield, current_ratio, payout_ratio).

The IDX financial-ratio source leaves dividend_yield and current_ratio empty.
This scraper fills those missing fields from Yahoo Finance's company info so
the value / quality / dividend screens can produce results.

Usage:
    uv run python scrape_yahoo_financial_fields.py               # all tickers
    uv run python scrape_yahoo_financial_fields.py --ticker BBCA
    uv run python scrape_yahoo_financial_fields.py --limit 50
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


def to_idx_units(value) -> float | None:
    """Convert a raw rupiah monetary value to IDX billions convention.

    ``financial_ratios`` stores revenue/net income in IDR billions (e.g. BBRI
    2024 revenue ≈ 172124.02), while yfinance exposes raw IDR. We divide by
    1e9 to keep the IDX convention consistent across all rows.
    """
    num = _safe_float(value)
    return None if num is None else num / 1_000_000_000.0


def _latest_vector(frame, row_name: str) -> float | None:
    """Return the newest annual value for a financial-statement row, or None.

    ``frame`` columns are sorted newest-first; the first non-NaN value is the
    most recent period's figure.
    """
    if frame is None or row_name not in frame.index:
        return None
    try:
        series = frame.loc[row_name]
    except Exception:
        return None
    for v in series:
        num = _safe_float(v)
        if num is not None:
            return num
    return None


_OCF_ROWS = (
    "Operating Cash Flow",
    "Total Cash From Operating Activities",
    "Cash Flowsfromusedin Operating Activities Direct",
    "Cash Flow From Operating Activities",
)

# Row names that hold pre-tax operating profit, in preference order. The exact
# label varies between issuers (and versions of yfinance's statements).
_OI_ROWS = (
    "Operating Income",
    "EBIT",
    "Operating Income (Loss)",
)

# Sourced from the income statement only when an explicit Operating Income / EBIT
# row is absent (most common for banks), so the engine can still derive operating
# margin, net debt/EBITDA and interest coverage deterministically.
_OPEX_ROWS = (
    "Operating Expense",
    "Total Operating Expenses",
)


def _latest_any(frame, row_names) -> float | None:
    """Return the newest annual value for the first row present in ``row_names``."""
    for name in row_names:
        val = _latest_vector(frame, name)
        if val is not None:
            return val
    return None


def compute_cagr(financials, row_name: str) -> float | None:
    """Return multi-year CAGR (decimal) for a financial statement row, or None.

    yfinance ``financials`` columns are sorted newest-first. Decades of columns
    may contain NaN for a period that was not reported; we treat them as
    missing (dropped for the value) but keep the number of years implied by the
    column count, so a ``[121, NaN, 100]`` series still spans 2 years and yields
    ``(121/100)**(1/2) - 1``.
    """
    if financials is None or row_name not in financials.index:
        return None
    try:
        series = list(financials.loc[row_name])
    except Exception:
        return None
    if len(series) < 2:
        return None
    years = max(len(series) - 1, 1)
    # Drop NaN/Inf but preserve the newest->oldest ordering, then flip to arrange
    # oldest -> newest so ``start``/``end`` are the true period boundaries.
    clean = [v for v in series if _safe_float(v) is not None]
    if len(clean) < 2:
        return None
    clean.reverse()
    start = _safe_float(clean[0])
    end = _safe_float(clean[-1])
    if start is None or end is None or start <= 0 or end <= 0:
        return None
    try:
        return (end / start) ** (1.0 / years) - 1.0
    except (ValueError, ZeroDivisionError):
        return None


def fetch_enrichment(yf_ticker: str) -> dict | None:
    """Return enrichment for one ticker: dividends/current-ratio, growth CAGRs,
    and the cash-flow / interest components used to derive gross margin,
    interest coverage, net debt/EBITDA and FCF margin.
    """
    try:
        ticker = yf.Ticker(yf_ticker)
        info = ticker.info or {}
        financials = ticker.financials
        balance = ticker.balance_sheet
        cashflow = ticker.cashflow
    except Exception as exc:  # pragma: no cover - network variance
        print(f"  Fetch failed for {yf_ticker}: {exc}")
        return None

    gross_profit = to_idx_units(_latest_vector(financials, "Gross Profit"))
    cash = to_idx_units(_latest_vector(balance, "Cash And Cash Equivalents"))
    interest_expense = to_idx_units(_latest_vector(financials, "Interest Expense"))
    operating_cash_flow = to_idx_units(_latest_any(cashflow, _OCF_ROWS))
    # yfinance reports capex as a negative outflow; store the magnitude.
    capex_raw = _latest_vector(cashflow, "Capital Expenditure")
    capital_expenditures = to_idx_units(abs(capex_raw)) if capex_raw is not None else None

    # Operating income: prefer the explicit Operating Income / EBIT row; otherwise
    # derive Revenue - Operating Expense (banks often omit the explicit row). The
    # value is stored in IDX billions so it is comparable with the other rows.
    operating_income = None
    revenue_raw = _latest_vector(financials, "Total Revenue")
    oi_raw = _latest_any(financials, _OI_ROWS)
    if oi_raw is not None:
        operating_income = to_idx_units(oi_raw)
    else:
        opex_raw = _latest_any(financials, _OPEX_ROWS)
        if revenue_raw is not None and opex_raw is not None:
            operating_income = to_idx_units(revenue_raw - opex_raw)

    values = {
        "ticker": to_idx_ticker(yf_ticker),
        "dividend_yield": info.get("dividendYield"),
        "current_ratio": info.get("currentRatio"),
        "payout_ratio": info.get("payoutRatio"),
        "revenue_cagr": compute_cagr(financials, "Total Revenue"),
        "earnings_cagr": compute_cagr(financials, "Net Income"),
        "eps_cagr": compute_cagr(financials, "Diluted EPS"),
        "gross_profit": gross_profit,
        "operating_income": operating_income,
        "cash_and_equivalents": cash,
        "interest_expense": interest_expense,
        "operating_cash_flow": operating_cash_flow,
        "capital_expenditures": capital_expenditures,
    }
    # Only return when at least one value is actually present.
    if all(v is None for k, v in values.items() if k != "ticker"):
        return None
    return values


def scrape_enrichments(
    tickers: list[str] | None = None,
    limit: int | None = None,
    offset: int = 0,
    delay_seconds: float = 0.3,
) -> int:
    """Scrape enrichment fields for tickers and persist to PostgreSQL."""
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

    print(f"Scraping enrichment fields for {len(tickers)} tickers...")
    updated = 0
    with ScraperDatabase() as store:
        for index, ticker in enumerate(tickers, start=1):
            print(f"[{index}/{len(tickers)}] {ticker}")
            record = fetch_enrichment(normalize_yf_ticker(ticker))
            if not record:
                print("  -> no enrichment data")
                continue
            store.update_financial_enrichments([record])
            print(f"  -> updated: div_yield={record['dividend_yield']}, "
                  f"current_ratio={record['current_ratio']}, payout_ratio={record['payout_ratio']}")
            updated += 1
            if delay_seconds:
                time.sleep(delay_seconds)
    print(f"Done. Enriched {updated} tickers.")
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape yfinance enrichment fields")
    parser.add_argument("--ticker", action="append", help="Specific ticker (repeatable)")
    parser.add_argument("--limit", type=int, help="Limit number of tickers (for testing)")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N tickers (for batching)")
    parser.add_argument("--delay", type=float, default=0.3, help="Delay between tickers (seconds)")
    args = parser.parse_args()

    scrape_enrichments(
        tickers=args.ticker,
        limit=args.limit,
        offset=args.offset,
        delay_seconds=args.delay,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
