"""Remove news articles whose ticker link fails the relevance gate.

``news_articles`` historically attributed rows to a company they do not mention:
Brave News Search queried ``"<TICKER> saham berita"`` and stored every result
with the query ticker, and ``enrich_news_tickers`` links by first ticker match
found in the text. An SICO (Sigma Energy Compressindo) query, for example, left
articles about Sigma Lithium / SigmaRoc tagged ``SICO``.

New rows are gated at ingest (see ``scrape_brave_news`` + ``news_relevance``);
this script cleans up rows already stored. Deletion is destructive, so the
default is a dry run — pass ``--apply`` to actually delete. ``news_impacts``
rows cascade from ``news_articles`` (ON DELETE CASCADE).

Usage:
    uv run python prune_irrelevant_news.py            # dry run (list only)
    uv run python prune_irrelevant_news.py --apply    # delete
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from database.scraper_store import ScraperDatabase
from news_relevance import article_text, is_relevant_news


def find_irrelevant_news(store: ScraperDatabase) -> list[tuple[int, str, str]]:
    """Return ``(id, ticker, title)`` for ticker-tagged rows failing the gate."""
    store._ensure_connection()
    assert store.connection is not None
    with store.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT n.id, n.ticker, n.title, n.content, c.name
            FROM news_articles n
            JOIN companies c ON c.ticker = n.ticker
            WHERE n.ticker IS NOT NULL
            ORDER BY n.id
            """
        )
        rows = cursor.fetchall()

    flagged: list[tuple[int, str, str]] = []
    for row_id, ticker, title, content, name in rows:
        if not is_relevant_news(article_text(title, content), ticker, name):
            flagged.append((row_id, ticker, title or ""))
    return flagged


def prune_irrelevant_news(apply: bool = False) -> dict:
    """Delete (or, by default, just list) news rows that fail the relevance gate."""
    with ScraperDatabase() as store:
        flagged = find_irrelevant_news(store)
        print(f"Scanned ticker-tagged news; {len(flagged)} fail the relevance gate.")
        for row_id, ticker, title in flagged:
            print(f"  [{row_id}] {ticker}: {title[:90]}")

        deleted = 0
        if not flagged:
            return {"irrelevant": 0, "deleted": 0}
        if not apply:
            print("Dry run: pass --apply to delete these rows.")
            return {"irrelevant": len(flagged), "deleted": 0}

        store._ensure_connection()
        assert store.connection is not None
        with store.connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM news_articles WHERE id = ANY(%s)",
                ([row_id for row_id, _, _ in flagged],),
            )
            deleted = cursor.rowcount
        store.connection.commit()
        print(f"Deleted {deleted} irrelevant news article(s); quotes/impacts cascade.")
        return {"irrelevant": len(flagged), "deleted": deleted}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Delete news articles not relevant to their linked ticker"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete the rows (default: dry run, list only)",
    )
    args = parser.parse_args()
    prune_irrelevant_news(apply=args.apply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
