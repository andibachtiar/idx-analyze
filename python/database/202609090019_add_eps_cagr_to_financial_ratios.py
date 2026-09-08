"""Add eps_cagr to financial_ratios (finalise the growth panel).

Backfills the earnings-per-share 3Y CAGR so the Analisa tab no longer shows
``eps_cagr_3y`` as unavailable. The value is computed by the yfinance
enrichment scraper (``scrape_yahoo_financial_fields``) and stored in the same
decimal convention as ``revenue_cagr`` / ``earnings_cagr``.

The store method ``_ensure_eps_cagr_column`` is an idempotent guard so the
API works even before/without the migration runner applying this file.
"""

name = "202609090019_add_eps_cagr_to_financial_ratios"


def up(cursor) -> None:
    cursor.execute(
        "ALTER TABLE financial_ratios ADD COLUMN IF NOT EXISTS eps_cagr NUMERIC"
    )


def down(cursor) -> None:
    cursor.execute("ALTER TABLE financial_ratios DROP COLUMN IF EXISTS eps_cagr")
