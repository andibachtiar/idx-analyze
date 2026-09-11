"""Periodic AI research re-analysis (Phase 17 — Auto-analyze berkala).

Analyzes watchlist/favorite tickers on a schedule, respecting a recency guard so
repeated runs do not spam the LLM. Reuses the same report + research-memory flow
as ``POST /stocks/{ticker}/research/analyze``: check ``ResearchMemory`` for a
report saved within the last ``min_hours``; if present, skip; otherwise run
``analyze_stock`` and persist via ``save_research_report``.

Environment:
    AUTO_ANALYZE_TICKERS   comma-separated override (default: favorites/watchlist)
    AUTO_ANALYZE_MIN_HOURS minimum hours between analyses per ticker (default 24)
    RESEARCH_ANALYZE_MIN_HOURS min hours between comprehensive candidate analyses
                           (default 168 = 1 week; source=research_candidates)
    AUTO_ANALYZE_ENABLED   scheduler integration toggle (default "false")

Usage:
    uv run python auto_analyze.py                     # favorites/watchlist
    uv run python auto_analyze.py --ticker BBCA --ticker BBRI
    uv run python auto_analyze.py --dry-run
    uv run python auto_analyze.py --force --limit 1
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from ai.memory import ResearchMemory, save_research_report
from ai.researcher import analyze_stock
from database.scraper_store import ScraperDatabase

# Recency guard defaults (hours). Comprehensive research-candidate analysis is
# intentionally less frequent (1 week) than the favorites/watchlist check (24h).
_AUTO_ANALYZE_MIN_HOURS_DEFAULT = 24.0
_RESEARCH_ANALYZE_MIN_HOURS_DEFAULT = 24.0 * 7  # 1 week


def _hours_since(iso: str | None) -> float | None:
    """Return hours between a saved/timestamp string and now, or None."""
    if not iso:
        return None
    try:
        when = datetime.fromisoformat(iso)
        now = datetime.now().astimezone()
        if when.tzinfo is None:
            when = when.replace(tzinfo=now.tzinfo)
        return (now - when).total_seconds() / 3600.0
    except (ValueError, TypeError):
        return None


def report_to_dict(report) -> dict:
    """Convert a ``ResearchReport`` object to the dict persisted in memory.

    Delegates to ``ai.report.report_to_dict`` so the pipeline stores exactly the
    same ``sections``/``claim_summary`` structure as the API endpoints (the
    ``claim_summary`` is derived from the report's inline claim markers rather
    than hardcoded to zeros).
    """
    from ai.report import report_to_dict as _report_to_dict

    return _report_to_dict(report)


def analyze_ticker(
    ticker: str,
    min_hours: float = 24.0,
    question: str = "",
    force: bool = False,
) -> dict:
    """Analyze one ticker, skipping if a fresh report exists within ``min_hours``."""
    memory = ResearchMemory()
    latest = memory.get_latest_report(ticker) if not force else None
    if latest:
        saved = latest.get("saved_at") or latest.get("generated_at")
        age = _hours_since(saved)
        if age is not None and age < min_hours:
            return {
                "status": "skipped", "ticker": ticker.upper(),
                "age_hours": round(age, 1), "min_hours": min_hours, "report": latest,
            }

    report = analyze_stock(ticker, question=question)
    result = report_to_dict(report) if hasattr(report, "ticker") else report
    # Attach a deterministic validator score so saved reports carry their own
    # quality audit (Phase 18k) — visible in research history and rankable.
    try:
        from ai.prompts.validator import enrich_with_validator

        result = enrich_with_validator(result)
    except Exception as e:
        print(f"Validator enrichment skipped for {ticker}: {e}")
    path = save_research_report(ticker, result, question=question)
    # Stamp the deterministic validator score onto any research_candidate rows
    # for this ticker so the Research tab can rank candidates by validity.
    try:
        with ScraperDatabase() as store:
            store.update_candidate_validity(
                ticker,
                result.get("validator_total"),
                result.get("validator_tier", ""),
            )
    except Exception as e:
        print(f"Candidate validity stamp skipped for {ticker}: {e}")
    return {"status": "analyzed", "ticker": ticker.upper(), "path": path}


def resolve_research_candidate_tickers(limit: int | None = None) -> list[str]:
    """Return distinct non-NULL tickers from the latest research candidates."""
    with ScraperDatabase() as store:
        store._ensure_connection()
        assert store.connection is not None
        with store.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT ticker
                FROM research_candidates
                WHERE ticker IS NOT NULL
                  AND candidate_date = (SELECT MAX(candidate_date) FROM research_candidates)
                ORDER BY ticker
                """
            )
            tickers = [row[0] for row in cursor.fetchall()]
    if limit:
        tickers = tickers[:limit]
    return tickers


def resolve_tickers(source: str = "favorites", limit: int | None = None) -> list[str]:
    """Return the ticker list to analyze: --ticker/env override, then by source.

    ``source`` is "favorites" (watchlist) or "research_candidates" (latest
    deterministic macro candidates). If ``AUTO_ANALYZE_TICKERS`` is set it always
    takes precedence.
    """
    env = os.environ.get("AUTO_ANALYZE_TICKERS", "").strip()
    if env:
        tickers = [t.strip().upper() for t in env.split(",") if t.strip()]
    elif source == "research_candidates":
        tickers = resolve_research_candidate_tickers(limit=limit)
        if not tickers:
            print("No research candidates with tickers found.")
            return []
    else:
        with ScraperDatabase() as store:
            tickers = store.get_favorites()
    if limit:
        tickers = tickers[:limit]
    return tickers


def run(
    limit: int | None = None,
    min_hours: float | None = None,
    force: bool = False,
    dry_run: bool = False,
    source: str = "favorites",
) -> int:
    """Run auto-analysis over the target tickers. Returns number analyzed."""
    effective_min = min_hours if min_hours is not None else float(
        os.environ.get(
            "RESEARCH_ANALYZE_MIN_HOURS"
            if source == "research_candidates"
            else "AUTO_ANALYZE_MIN_HOURS",
            str(
                _RESEARCH_ANALYZE_MIN_HOURS_DEFAULT
                if source == "research_candidates"
                else _AUTO_ANALYZE_MIN_HOURS_DEFAULT
            ),
        )
    )
    # Cap the number of research-candidate tickers per run to control LLM cost.
    if source == "research_candidates" and limit is None:
        limit = int(os.environ.get("RESEARCH_ANALYZE_MAX_TICKERS", "20"))
    tickers = resolve_tickers(source=source, limit=limit)
    if not tickers:
        print("No tickers to auto-analyze (set AUTO_ANALYZE_TICKERS, -source research_candidates, or add favorites).")
        return 0

    print(f"Auto-analyzing {len(tickers)} ticker(s) | min_hours={effective_min} | force={force}")
    done = {"analyzed": 0, "skipped": 0, "failed": 0}
    for t in tickers:
        if dry_run:
            print(f"  [dry-run] {t}")
            continue
        try:
            r = analyze_ticker(t, min_hours=effective_min, force=force)
        except Exception as e:
            # A provider failure on one ticker must not abort the whole run.
            print(f"  {t}: failed: {e}")
            done["failed"] += 1
            continue
        extra = f" (age {r['age_hours']}h)" if r.get("age_hours") is not None else ""
        print(f"  {t}: {r['status']}{extra}")
        done[r["status"]] = done.get(r["status"], 0) + 1
    print(f"Done. analyzed={done['analyzed']} skipped={done['skipped']} failed={done['failed']}")
    return done["analyzed"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Auto-analyze tickers periodically (recency-guarded)"
    )
    parser.add_argument("--ticker", action="append", help="Ticker(s) to analyze")
    parser.add_argument(
        "--source",
        choices=["favorites", "research_candidates"],
        default="favorites",
        help="Ticker source (default favorites/watchlist; or latest research candidates)",
    )
    parser.add_argument("--limit", type=int, help="Limit number of tickers")
    parser.add_argument("--min-hours", type=float, help="Recency guard (hours)")
    parser.add_argument("--force", action="store_true", help="Ignore recency guard")
    parser.add_argument("--dry-run", action="store_true", help="Print plan only")
    args = parser.parse_args()

    if args.ticker:
        os.environ["AUTO_ANALYZE_TICKERS"] = ",".join(args.ticker)

    run(
        limit=args.limit,
        min_hours=args.min_hours,
        force=args.force,
        dry_run=args.dry_run,
        source=args.source,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
