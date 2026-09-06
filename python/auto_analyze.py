"""Periodic AI research re-analysis (Phase 17 — Auto-analyze berkala).

Analyzes watchlist/favorite tickers on a schedule, respecting a recency guard so
repeated runs do not spam the LLM. Reuses the same report + research-memory flow
as ``POST /stocks/{ticker}/research/analyze``: check ``ResearchMemory`` for a
report saved within the last ``min_hours``; if present, skip; otherwise run
``analyze_stock`` and persist via ``save_research_report``.

Environment:
    AUTO_ANALYZE_TICKERS   comma-separated override (default: favorites/watchlist)
    AUTO_ANALYZE_MIN_HOURS minimum hours between analyses per ticker (default 24)
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

# Fields the research endpoint exposes (see api/main.py _research_report_to_dict).
_REPORT_FIELDS = [
    "executive_summary", "business_quality", "growth_analysis", "profitability",
    "financial_health", "valuation", "technical_position", "recent_events",
    "risks", "bull_case", "base_case", "bear_case", "conclusion",
]


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
    """Convert a ``ResearchReport`` object to the dict persisted in memory."""
    result = {
        "ticker": report.ticker,
        "question": getattr(report, "question", ""),
        "generated_at": (getattr(report, "timestamp", None) or datetime.now()).isoformat(),
        "confidence_score": getattr(report, "confidence", None),
    }
    for field in _REPORT_FIELDS:
        result[field] = getattr(report, field, "")
    return result


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
    path = save_research_report(ticker, result, question=question)
    return {"status": "analyzed", "ticker": ticker.upper(), "path": path}


def resolve_tickers() -> list[str]:
    """Return override env tickers, else favorites/watchlist from PostgreSQL."""
    env = os.environ.get("AUTO_ANALYZE_TICKERS", "").strip()
    if env:
        return [t.strip().upper() for t in env.split(",") if t.strip()]
    with ScraperDatabase() as store:
        return store.get_favorites()


def run(
    limit: int | None = None,
    min_hours: float | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> int:
    """Run auto-analysis over the target tickers. Returns number analyzed."""
    effective_min = min_hours if min_hours is not None else float(
        os.environ.get("AUTO_ANALYZE_MIN_HOURS", "24")
    )
    tickers = resolve_tickers()
    if not tickers:
        print("No tickers to auto-analyze (set AUTO_ANALYZE_TICKERS or add favorites).")
        return 0
    if limit:
        tickers = tickers[:limit]

    print(f"Auto-analyzing {len(tickers)} ticker(s) | min_hours={effective_min} | force={force}")
    done = {"analyzed": 0, "skipped": 0}
    for t in tickers:
        if dry_run:
            print(f"  [dry-run] {t}")
            continue
        r = analyze_ticker(t, min_hours=effective_min, force=force)
        extra = f" (age {r['age_hours']}h)" if r.get("age_hours") is not None else ""
        print(f"  {t}: {r['status']}{extra}")
        done[r["status"]] = done.get(r["status"], 0) + 1
    print(f"Done. analyzed={done['analyzed']} skipped={done['skipped']}")
    return done["analyzed"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Auto-analyze tickers periodically (recency-guarded)"
    )
    parser.add_argument("--ticker", action="append", help="Ticker(s) to analyze")
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
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
