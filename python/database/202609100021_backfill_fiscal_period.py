"""Backfill fiscal_period for IDX rows that stored it as NULL.

IDX reports quarterly snapshots with period ends on Mar 31 / Jun 30 / Sep 30
and an annual snapshot on Dec 31. The IDX JSON feed does not carry an explicit
quarter, so ``upsert_financial_ratios`` left ``fiscal_period`` NULL for every
row (see backlog #6). This migration recovers the quarter from ``period_end``:
Mar=1, Jun=2, Sep=3; December stays NULL because it is the full fiscal year
(annual). The same month heuristic is used by ``analysis/historical.py`` and the
scraper store helper ``_period_from_date``.
"""

name = "202609100021_backfill_fiscal_period"


def up(cursor) -> None:
    cursor.execute(
        """
        UPDATE financial_ratios
        SET fiscal_period = CASE
            WHEN EXTRACT(MONTH FROM period_end) = 3  THEN 1
            WHEN EXTRACT(MONTH FROM period_end) = 6  THEN 2
            WHEN EXTRACT(MONTH FROM period_end) = 9  THEN 3
            ELSE NULL
        END
        WHERE fiscal_period IS NULL
          AND period_end IS NOT NULL
          AND EXTRACT(MONTH FROM period_end) IN (3, 6, 9)
        """
    )


def down(cursor) -> None:
    # One-way attribution: there is no safe inverse (we cannot tell which of the
    # now-set periods were originally NULL vs provided by the source). Nothing
    # to roll back.
    pass
