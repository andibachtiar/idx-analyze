"""Widen financial numeric columns for IDX source values."""

name = "202608270007_widen_financial_numeric_columns"


# PostgreSQL NUMERIC without a precision limit preserves source values and
# avoids rejecting valid large absolute financial statement amounts.
_COLUMNS = (
    "eps",
    "gross_margin",
    "operating_margin",
    "net_margin",
    "roe",
    "roa",
    "roic",
    "debt_to_equity",
    "current_ratio",
    "interest_coverage",
    "pe_ratio",
    "pb_ratio",
    "ev_ebitda",
    "dividend_yield",
)


def up(cursor) -> None:
    for column in _COLUMNS:
        cursor.execute(
            f"ALTER TABLE financial_ratios ALTER COLUMN {column} TYPE NUMERIC"
        )


def down(cursor) -> None:
    # Reverting can fail if existing values exceed NUMERIC(9,4). This is
    # intentionally explicit rather than silently losing source precision.
    for column in _COLUMNS:
        cursor.execute(
            f"ALTER TABLE financial_ratios ALTER COLUMN {column} TYPE NUMERIC(9,4)"
        )
