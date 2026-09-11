"""Fix financial_ratios idempotency: NULL fiscal_period defeated the UNIQUE.

The table-level UNIQUE (ticker, fiscal_year, fiscal_period) never fired because
``fiscal_period`` is NULL for every row (IDX reports annual figures without a
quarter), and PostgreSQL treats NULLs as distinct in a unique index. As a
result every pipeline run re-inserted the same period, inflating the table to
~7.6k rows for ~2.9k real periods (up to 6 copies each, e.g. SICO FY2024).

Duplicates are not field-identical: some copies carry yfinance enrichment
(``current_ratio``, ``dividend_yield``) while later copies carry
``operating_income``. Deleting copies blindly would lose complementary data, so
this migration merges each group's non-NULL values (newest row wins) into a
single keeper before deleting the rest.

It then replaces the never-firing UNIQUE with a unique expression index on
(ticker, fiscal_year, COALESCE(fiscal_period, 0), period_end). ``period_end``
must be part of the key: one (ticker, fiscal_year) pair (BLOG 2024) has two
distinct period ends.
"""

name = "202609100020_fix_financial_ratios_dedup"

# Managed columns are not merged/compared between duplicate rows.
_EXCLUDED = {
    "id",
    "ticker",
    "fiscal_year",
    "fiscal_period",
    "period_end",
    "source",
    "created_at",
    "updated_at",
}


def _data_columns(cursor) -> list[str]:
    """Return the mergeable data columns present in the live schema.

    Discovered dynamically (via information_schema) so the migration works
    regardless of which enrichment migrations have already run.
    """
    cursor.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'financial_ratios' ORDER BY ordinal_position"
    )
    return [r["column_name"] for r in cursor.fetchall() if r["column_name"] not in _EXCLUDED]


def up(cursor) -> None:
    data_columns = _data_columns(cursor)
    quoted = ", ".join(f'"{c}"' for c in data_columns)

    cursor.execute(
        f"SELECT id, ticker, fiscal_year, fiscal_period, period_end, {quoted} "
        "FROM financial_ratios "
        "ORDER BY ticker, fiscal_year, period_end NULLS LAST, id"
    )

    groups: dict[tuple, list[dict]] = {}
    for row in cursor.fetchall():
        key = (
            row["ticker"],
            row["fiscal_year"],
            row["fiscal_period"] or 0,
            row["period_end"],
        )
        groups.setdefault(key, []).append(row)

    delete_ids: list[int] = []
    for rows in groups.values():
        if len(rows) <= 1:
            continue
        keeper = rows[-1]  # highest id: rows are ordered by id within a group
        merged: dict[str, object] = {}
        for row in rows:  # ascending id -> newest non-NULL value wins
            for col in data_columns:
                if row[col] is not None:
                    merged[col] = row[col]
        assignments = ", ".join(f'"{c}" = %s' for c in data_columns)
        cursor.execute(
            f"UPDATE financial_ratios SET {assignments} WHERE id = %s",
            [merged.get(c) for c in data_columns] + [keeper["id"]],
        )
        delete_ids.extend(row["id"] for row in rows[:-1])

    if delete_ids:
        cursor.execute("DELETE FROM financial_ratios WHERE id = ANY(%s)", (delete_ids,))

    # Replace the never-firing UNIQUE with a NULL-correct expression index.
    cursor.execute(
        "ALTER TABLE financial_ratios DROP CONSTRAINT IF EXISTS "
        "financial_ratios_ticker_fiscal_year_fiscal_period_key"
    )
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS financial_ratios_period_uniq_idx "
        "ON financial_ratios "
        "(ticker, fiscal_year, COALESCE(fiscal_period, 0), period_end)"
    )


def down(cursor) -> None:
    cursor.execute("DROP INDEX IF EXISTS financial_ratios_period_uniq_idx")
    cursor.execute(
        "ALTER TABLE financial_ratios ADD CONSTRAINT "
        "financial_ratios_ticker_fiscal_year_fiscal_period_key "
        "UNIQUE (ticker, fiscal_year, fiscal_period)"
    )
