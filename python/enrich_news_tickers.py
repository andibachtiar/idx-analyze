"""
Enrich news_articles with a known ticker extracted from the article text.

The IDX GetNewsSearch feed returns general announcements with no ticker field.
This links each article to a company by matching a known IDX ticker appearing
as a whole word in the title (falling back to content), so news can be shown
per-stock and fed into the event pipeline.

Usage:
    uv run python enrich_news_tickers.py                 # process all news
    uv run python enrich_news_tickers.py --limit 100
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Iterable

sys.path.insert(0, os.path.dirname(__file__))

from database.scraper_store import ScraperDatabase

# Common Indonesian words / acronyms that happen to look like a ticker code.
# These are excluded so they are not wrongly linked (e.g. "Bank BCA" -> BANK).
STOPWORDS = {
    "AND", "ATM", "API", "ASIA", "BANK", "BI", "BPS", "BUMN", "CEO",
    "CFO", "COO", "DPR", "ESG", "FMCG", "GDP", "IDX", "IMF", "IPO", "IQ",
    "IT", "KPU", "MD", "NPS", "OJK", "PAPUA", "PM", "RI", "SDA", "SUS",
    "TPA", "UMKM", "UN", "WTO", "BUMN", "MM", "RR", "TB", "Tbk", "TK",
}


def compile_ticker_pattern(tickers: Iterable[str]) -> re.Pattern:
    """Build a case-sensitive regex matching a known ticker typed in UPPERCASE.

    Stock codes are rendered in uppercase on official IDX announcements, so we
    match the literal ticker (uppercase) as a whole word. Lowercase/common words
    like "Bank" are ignored, avoiding false positives.
    """
    words = sorted(
        {t.strip().upper() for t in tickers if t and t.strip() and t.strip().upper() not in STOPWORDS},
        reverse=True,
    )
    return re.compile(r"\b(?:%s)\b" % "|".join(re.escape(w) for w in words))


def extract_ticker(text: str, pattern: re.Pattern) -> str | None:
    """Return the first known ticker found as an uppercase whole word, or None."""
    if not text:
        return None
    match = pattern.search(text)
    return match.group(0) if match else None


def enrich_news_tickers(limit: int | None = None) -> int:
    """Set news_articles.ticker from the article text when it is missing."""
    with ScraperDatabase() as store:
        store._ensure_connection()
        assert store.connection is not None
        with store.connection.cursor() as cursor:
            cursor.execute("SELECT ticker FROM companies")
            tickers = [row[0] for row in cursor.fetchall()]
        if not tickers:
            print("No companies to match against.")
            return 0
        pattern = compile_ticker_pattern(tickers)

        with store.connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, title, content FROM news_articles WHERE ticker IS NULL ORDER BY id"
            )
            rows = cursor.fetchall()

        if limit:
            rows = rows[:limit]

        updates = []
        for row_id, title, content in rows:
            ticker = extract_ticker(title or "", pattern) or extract_ticker(content or "", pattern)
            if ticker:
                updates.append((ticker, row_id))

        if not updates:
            print("No news tickers could be resolved.")
            return 0

        with store.connection.cursor() as cursor:
            from psycopg2.extras import execute_values
            execute_values(
                cursor,
                "UPDATE news_articles AS n SET ticker = data.ticker FROM (VALUES %s) AS data(ticker, id) WHERE n.id = data.id",
                updates,
            )
        store.connection.commit()
        print(f"Linked {len(updates)} news articles to a ticker.")
        return len(updates)


def main() -> int:
    parser = argparse.ArgumentParser(description="Link news_articles to known IDX tickers")
    parser.add_argument("--limit", type=int, help="Limit number of articles (for testing)")
    args = parser.parse_args()
    enrich_news_tickers(limit=args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
