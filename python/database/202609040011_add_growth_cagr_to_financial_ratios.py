"""Add revenue/earnings CAGR columns to financial_ratios for growth screening."""

name = "202609040011_add_growth_cagr_to_financial_ratios"


def up(cursor) -> None:
    cursor.execute("ALTER TABLE financial_ratios ADD COLUMN IF NOT EXISTS revenue_cagr NUMERIC")
    cursor.execute("ALTER TABLE financial_ratios ADD COLUMN IF NOT EXISTS earnings_cagr NUMERIC")


def down(cursor) -> None:
    cursor.execute("ALTER TABLE financial_ratios DROP COLUMN IF EXISTS revenue_cagr")
    cursor.execute("ALTER TABLE financial_ratios DROP COLUMN IF EXISTS earnings_cagr")
