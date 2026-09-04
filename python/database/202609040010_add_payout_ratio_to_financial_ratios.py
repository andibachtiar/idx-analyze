"""Add payout_ratio to financial_ratios for dividend screening."""

name = "202609040010_add_payout_ratio_to_financial_ratios"


def up(cursor) -> None:
    cursor.execute("ALTER TABLE financial_ratios ADD COLUMN IF NOT EXISTS payout_ratio NUMERIC")


def down(cursor) -> None:
    cursor.execute("ALTER TABLE financial_ratios DROP COLUMN IF EXISTS payout_ratio")
