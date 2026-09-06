"""
Scrape latest news via Brave Search API into PostgreSQL (Fase A).

Queries Brave News Search per ticker, normalises results to the ``news_articles``
schema (idempotent via ``news_code = sha1(url)``), and (optionally) filters
results by an allowlist of news publisher sources configured in the environment
so we don't ingest news from just anywhere.

Environment (loaded from project .env):
    BRAVE_API_KEY       (required)  Brave Search subscription token
    BRAVE_URL           (default https://api.search.brave.com/res/v1/news/search)
    BRAVE_COUNT       (default 5)          results per query
    BRAVE_COUNTRY     (default id)
    BRAVE_LANG        (default "" -> omitted; Brave rejects search_lang="id")
    BRAVE_FRESHNESS   (default "" -> omitted)  e.g. pd/pw/pm/py or a date range
    BRAVE_SOURCES     comma-separated ALLOWED publisher domains / names.
                        Empty = accept all (not recommended). e.g.
                        "cnbcindonesia.com,antaranews.com,katadata.co.id,bisnis.com"
    BRAVE_MACRO_QUERIES  comma-separated general economic/political search queries
                        used by ``--macro`` mode (stored with ticker=NULL). e.g.
                        "ekonomi indonesia, bi suku bunga, harga batubara, ihsg"

Usage:
    uv run python scrape_brave_news.py --ticker BBCA --ticker BBRI
    uv run python scrape_brave_news.py --macro                 # use BRAVE_MACRO_QUERIES
    uv run python scrape_brave_news.py --macro --macro-queries "ekonomi indonesia,ihsg"
    uv run python scrape_brave_news.py --source cnbcindonesia.com,katadata.co.id
    uv run python scrape_brave_news.py --limit 10 --delay 1.0
"""

from __future__ import annotations

import argparse
import hashlib
import os
import time
from pathlib import Path

from curl_cffi import requests
from dotenv import load_dotenv

from database.scraper_store import ScraperDatabase

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DEFAULT_URL = "https://api.search.brave.com/res/v1/news/search"


# =============================================================================
# CONFIG
# =============================================================================

def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def get_config() -> dict:
    """Return Brave config from environment, including the source allowlist."""
    return {
        "api_key": _env("BRAVE_API_KEY"),
        "url": _env("BRAVE_URL", DEFAULT_URL),
        "count": int(_env("BRAVE_COUNT", "5") or 5),
        # country / search_lang / freshness are optional; only sent when non-empty
        # because Brave's enum rejects unknown/unsupported values (e.g. search_lang=id -> 422).
        "country": _env("BRAVE_COUNTRY", "id"),
        "lang": _env("BRAVE_LANG", ""),
        "freshness": _env("BRAVE_FRESHNESS", ""),
        # Comma-separated allowed publisher domains / names, lowercased & trimmed.
        "sources": [s.strip().lower() for s in _env("BRAVE_SOURCES", "").split(",") if s.strip()],
        # Comma-separated general/macro queries (e.g. "ekonomi indonesia, bi suku bunga, harga batubara, ihsg").
        "macro_queries": [q.strip() for q in _env("BRAVE_MACRO_QUERIES", "").split(",") if q.strip()],
    }


# =============================================================================
# QUERY + FETCH
# =============================================================================

def build_query(ticker: str, country: str = "id", lang: str = "id") -> str:
    """Return the search query and URL for one ticker (Indonesian news)."""
    return f"{ticker} saham berita"


def fetch_brave_news(cfg: dict, query: str) -> list[dict]:
    """Fetch Brave News results for a query. Returns raw 'news' items ([] on error)."""
    if not cfg.get("api_key"):
        print("  ! BRAVE_API_KEY not set; aborting fetch.")
        return []
    params = {"q": query, "count": cfg["count"]}
    # Only send country/search_lang when configured; Brave's enum rejects unknown values.
    if cfg.get("country"):
        params["country"] = cfg["country"]
    if cfg.get("lang"):
        params["search_lang"] = cfg["lang"]
    if cfg.get("freshness"):
        # Bias toward recent news (pd/pw/pm/py) to avoid the stale IDX feed.
        params["freshness"] = cfg["freshness"]
    # NOTE: no 'source' or 'search_lang=id' here — both caused HTTP 422 on this endpoint.

    # Log the exact request so it can be reproduced in Postman. The API key is
    # masked (only last 4 chars) to avoid leaking the secret into logs.
    import urllib.parse
    qs = urllib.parse.urlencode(params)
    key_prefix = cfg["api_key"][:4] + "****" + cfg["api_key"][-4:] if len(cfg["api_key"]) > 8 else "****"
    print(f"  [REQUEST] GET {cfg['url']}?{qs}")
    print(f"  [HEADER]  X-Subscription-Token: {key_prefix}")
    print("  [HEADER]  Accept: application/json")

    try:
        resp = requests.get(
            cfg["url"],
            params=params,
            headers={"X-Subscription-Token": cfg["api_key"], "Accept": "application/json"},
            timeout=20,
            impersonate="chrome",
        )
        if resp.status_code >= 400:
            # Surface response body so 4xx/5xx issues are diagnosable.
            print(f"  ! Brave HTTP {resp.status_code}: {resp.text[:300]}")
            return []
        data = resp.json()
        # Brave News Search returns items under top-level ``results``; ``news`` is a
        # fallback for forward-compatibility.
        if isinstance(data, dict):
            return data.get("results") or data.get("news") or []
        return []
    except Exception as exc:  # pragma: no cover - network variance
        print(f"  ! Brave fetch failed: {exc}")
        return []


def _stable_hash(value) -> str:
    """Deterministic sha1 (dedup key, stable across processes)."""
    return hashlib.sha1(str(value or "").encode("utf-8", errors="ignore")).hexdigest()


# =============================================================================
# SOURCE FILTER (allowlist)
# =============================================================================

def item_source(item: dict) -> str:
    """Best-effort publisher name for a Brave news item.

    Brave News returns the publisher under ``profile.name`` (with ``profile.url``),
    and the domain under ``meta_url.hostname``. We also accept a legacy
    ``source`` dict (publisher/name/url) for forward-compatibility.
    """
    profile = item.get("profile") or {}
    if isinstance(profile, dict):
        return str(profile.get("name") or profile.get("url") or "")
    meta = item.get("meta_url") or {}
    if isinstance(meta, dict):
        return str(meta.get("hostname") or meta.get("netloc") or "")
    src = item.get("source") or {}
    if isinstance(src, dict):
        return str(src.get("publisher") or src.get("name") or src.get("url") or "")
    return str(src or "")


def item_source_url(item: dict) -> str:
    """Source URL/domain for a Brave news item, if present."""
    meta = item.get("meta_url") or {}
    if isinstance(meta, dict):
        return str(meta.get("hostname") or meta.get("netloc") or "")
    profile = item.get("profile") or {}
    if isinstance(profile, dict):
        return str(profile.get("url") or "")
    src = item.get("source") or {}
    if isinstance(src, dict):
        return str(src.get("url") or src.get("domain") or "")
    return ""


def source_allowed(item: dict, allowed: list[str]) -> bool:
    """Return True if the item's source matches the allowlist (or list is empty).

    Matches against BOTH the publisher name and the publisher URL so an allowlist
    entry can be a domain (``cnbcindonesia.com``) or a publisher name ("CNBC Indonesia").
    """
    if not allowed:
        return True
    name = item_source(item).lower()
    url = item_source_url(item).lower()
    if not name and not url:
        return False
    for token in allowed:
        if token in name or token in url:
            return True
    return False


# =============================================================================
# NORMALIZE + PERSIST
# =============================================================================

def normalize_item(item: dict, ticker: str | None) -> dict | None:
    """Map a Brave news item to the ``news_articles`` schema (or None if unusable).

    ``ticker`` may be ``None`` for general/macro news (stored without a ticker).
    """
    title = str(item.get("title") or "").strip()
    url = str(item.get("url") or "").strip()
    if not title or not url:
        return None
    return {
        "ticker": ticker.upper() if ticker else None,
        "title": title,
        "url": url,
        "content": str(item.get("description") or "").strip() or None,
        "source": item_source(item),
        # Brave gives the ISO timestamp under ``page_age``; ``age`` is a human
        # string ("1 day ago") and must not be stored in a datetime column.
        "publishedAt": item.get("page_age") or item.get("published_at"),
        "newsCode": _stable_hash(url),
    }


def _filter_and_insert(store: ScraperDatabase, cfg: dict, items: list[dict], ticker: str | None) -> int:
    """Filter a raw Brave result list by source, normalize, and insert. Returns inserted count.

    Shared by the per-ticker (``scrape_brave_news``) and general/macro (``scrape_brave_macro``)
    modes so filtering, source-diagnostics, and persistence stay identical.
    """
    kept = []
    dropped = 0
    dropped_sources: list[str] = []
    for item in items:
        if not source_allowed(item, cfg["sources"]):
            dropped += 1
            src = item_source(item) or item_source_url(item)
            # Keep a small list of dropped publisher names so the user can extend
            # BRAVE_SOURCES when the allowlist is too narrow.
            if src and src not in dropped_sources:
                dropped_sources.append(src)
            continue
        rec = normalize_item(item, ticker)
        if rec:
            kept.append(rec)
    if kept:
        n = store.insert_news(kept)
        print(f"  -> fetched {len(items)}, kept {len(kept)}, inserted {n}" + (f", dropped {dropped}" if dropped else ""))
    else:
        n = 0
        print(f"  -> fetched {len(items)}, none kept (source filter)" + (f", dropped {dropped}" if dropped else ""))
    if cfg["sources"] and dropped_sources:
        print(f"     dropped sources: {', '.join(dropped_sources[:8])}")
        print("     -> add any of these to BRAVE_SOURCES to keep them")
    return n


def scrape_brave_news(
    tickers: list[str] | None = None,
    count: int | None = None,
    delay: float = 1.0,
    offset: int = 0,
    limit: int | None = None,
    allowed_sources: list[str] | None = None,
) -> int:
    """Run Brave news scraping for tickers and persist to PostgreSQL.

    When ``tickers`` is None the favorites/watchlist is used (cost-controlled).
    """
    cfg = get_config()
    if count:
        cfg["count"] = count
    if allowed_sources is not None:
        cfg["sources"] = [s.strip().lower() for s in allowed_sources if s.strip()]

    if tickers is None:
        with ScraperDatabase() as store:
            tickers = store.get_favorites()
        if not tickers:
            print("No favorites/watchlist found; pass --ticker or add favorites first.")
            return 0
        print(f"Using favorites/watchlist: {tickers}")

    tickers = tickers[offset:]
    if limit:
        tickers = tickers[:limit]

    print(
        f"Scraping Brave news for {len(tickers)} ticker(s) | "
        f"count={cfg['count']} | source filter={'ON' if cfg['sources'] else 'OFF (all)'}"
    )
    persisted = 0
    with ScraperDatabase() as store:
        for index, ticker in enumerate(tickers, start=1):
            print(f"[{index}/{len(tickers)}] {ticker}")
            items = fetch_brave_news(cfg, build_query(ticker, cfg["country"], cfg["lang"]))
            persisted += _filter_and_insert(store, cfg, items, ticker)
            if delay:
                time.sleep(delay)
    print(f"Done. Inserted {persisted} news records.")
    return persisted


def scrape_brave_macro(
    queries: list[str] | None = None,
    count: int | None = None,
    delay: float = 1.0,
    limit: int | None = None,
    allowed_sources: list[str] | None = None,
) -> int:
    """Fetch general economic/political news and persist with ``ticker=NULL``.

    Uses ``BRAVE_MACRO_QUERIES`` (or an explicit ``queries`` list) instead of
    per-ticker queries. Results are still filtered by ``BRAVE_SOURCES`` and stored
    idempotently, then can be linked to tickers/sectors in later phases.
    """
    cfg = get_config()
    if count:
        cfg["count"] = count
    if allowed_sources is not None:
        cfg["sources"] = [s.strip().lower() for s in allowed_sources if s.strip()]

    if not queries:
        queries = cfg["macro_queries"]
    if not queries:
        print("No BRAVE_MACRO_QUERIES configured; pass --macro-queries or set the env var.")
        return 0

    if limit:
        queries = queries[:limit]

    print(
        f"Scraping Brave macro news for {len(queries)} query(ies) | "
        f"count={cfg['count']} | source filter={'ON' if cfg['sources'] else 'OFF (all)'}"
    )
    persisted = 0
    with ScraperDatabase() as store:
        for index, query in enumerate(queries, start=1):
            print(f"[{index}/{len(queries)}] {query}")
            items = fetch_brave_news(cfg, query)
            # General/macro news is stored without a ticker (None).
            persisted += _filter_and_insert(store, cfg, items, None)
            if delay:
                time.sleep(delay)
    print(f"Done. Inserted {persisted} macro news records.")
    return persisted


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape news via Brave Search API")
    parser.add_argument("--ticker", action="append", help="Specific ticker (repeatable)")
    parser.add_argument("--macro", action="store_true", help="Run general macro/political queries (ticker=NULL)")
    parser.add_argument("--macro-queries", help="Comma-separated macro queries (overrides BRAVE_MACRO_QUERIES)")
    parser.add_argument("--limit", type=int, help="Limit number of tickers/queries (for testing)")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N tickers")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between queries (s)")
    parser.add_argument("--count", type=int, default=None, help="Results per query (default env)")
    parser.add_argument("--source", help="Comma-separated allowed sources (overrides env)")
    args = parser.parse_args()

    allowed = [s.strip() for s in args.source.split(",")] if args.source else None
    if args.macro:
        queries = [q.strip() for q in args.macro_queries.split(",")] if args.macro_queries else None
        scrape_brave_macro(
            queries=queries,
            count=args.count,
            delay=args.delay,
            limit=args.limit,
            allowed_sources=allowed,
        )
    else:
        scrape_brave_news(
            tickers=args.ticker,
            count=args.count,
            delay=args.delay,
            offset=args.offset,
            limit=args.limit,
            allowed_sources=allowed,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
