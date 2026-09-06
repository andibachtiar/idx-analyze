"""Fix news_impacts dedup: NULL ticker rows were not deduped (Fase B5 P0).

The original table-level UNIQUE (news_id, sector, ticker, direction) treated the
NULL ``ticker`` of sector-level rows as distinct (PostgreSQL NULL semantics), so
every pipeline run re-inserted the same sector-level impact, inflating counts and
net_strength in the macro snapshot/interpretation.

This migration:
  1. deletes duplicate sector-level rows (keeps one per the same
     news_id/sector/direction by preferring the row with the most complete
     matched_keywords, ties -> lowest id), and
  2. replaces the buggy UNIQUE with a unique expression index on
     (news_id, sector, COALESCE(ticker, ''), direction).
"""

name = "202609050014_fix_news_impacts_dedup"


def up(cursor) -> None:
    # 1. Deduplicate sector-level (ticker NULL) rows, keep the most complete one.
    cursor.execute(
        """
        DELETE FROM news_impacts
        WHERE id NOT IN (
            SELECT DISTINCT ON (news_id, sector, direction) id
            FROM news_impacts
            WHERE ticker IS NULL
            ORDER BY
                news_id, sector, direction,
                LENGTH(COALESCE(matched_keywords, '')) DESC,
                id ASC
        )
        """
    )
    # 2. Drop the old table-level UNIQUE constraint.
    cursor.execute(
        "ALTER TABLE news_impacts DROP CONSTRAINT IF EXISTS "
        "news_impacts_news_id_sector_ticker_direction_key"
    )
    # 3. Add the NULL-correct unique expression index.
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS news_impacts_uniq_idx "
        "ON news_impacts (news_id, sector, COALESCE(ticker, ''), direction)"
    )


def down(cursor) -> None:
    cursor.execute("DROP INDEX IF EXISTS news_impacts_uniq_idx")
    cursor.execute(
        "ALTER TABLE news_impacts ADD CONSTRAINT "
        "news_impacts_news_id_sector_ticker_direction_key "
        "UNIQUE (news_id, sector, ticker, direction)"
    )
