"""Daily research-candidate generation (Fase B5).

After the macro news pipeline (``news_brave`` -> ``news_impacts``), this script
runs ``generate_research_candidates`` to produce a deterministic list of the
sectors/companies most pressured by recent macro news, optionally asking the LLM
to interpret that same evidence, and persists the result idempotently to
``research_candidates`` (one row per date/sector/ticker/direction).

Sectors and tickers are NEVER invented by the LLM (Option A): the candidate list
comes from the ``news_impacts`` snapshot (affected tickers of high-pressure
sectors). The LLM only produces a narrative interpretation. It is a
deterministic-first, LLM-interpretation-only layer.

Environment:
    RESEARCH_CANDIDATES_MIN_HOURS  lookback window (default 48)
    RESEARCH_CANDIDATES_TOP_SECTORS top sectors (default 10)
    RESEARCH_CANDIDATES_MIN_NET    minimum |net_strength| for a candidate (default 0.25)
    RESEARCH_CANDIDATES_USE_LLM    "true"/"1" to interpret with the LLM (default "false")

Usage:
    uv run python generate_research_candidates.py                 # deterministic, 48h
    uv run python generate_research_candidates.py --use-llm       # + LLM interpretation
    uv run python generate_research_candidates.py --hours 24 --min-net 1.0
    uv run python generate_research_candidates.py --dry-run
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from ai.llm import LLMClient
from ai.prompts.macro_impact import generate_research_candidates as _generate


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate deterministic macro research candidates (Fase B5)"
    )
    parser.add_argument("--hours", type=int, default=int(os.getenv("RESEARCH_CANDIDATES_MIN_HOURS", "48")))
    parser.add_argument("--top-sectors", type=int, default=int(os.getenv("RESEARCH_CANDIDATES_TOP_SECTORS", "10")))
    parser.add_argument("--min-net", type=float, default=float(os.getenv("RESEARCH_CANDIDATES_MIN_NET", "0.25")))
    parser.add_argument("--use-llm", action="store_true", default=os.getenv("RESEARCH_CANDIDATES_USE_LLM", "").lower() in ("1", "true"))
    parser.add_argument("--max-tickers", type=int, default=int(os.getenv("RESEARCH_CANDIDATES_MAX_TICKERS_PER_SECTOR", "8")))
    parser.add_argument("--ticker-rank", choices=["technical", "liquidity"], default=os.getenv("RESEARCH_CANDIDATES_TICKER_RANK", "technical"))
    parser.add_argument("--baseline-days", type=int, default=int(os.getenv("RESEARCH_CANDIDATES_BASELINE_DAYS", "30")))
    parser.add_argument("--min-sample-days", type=int, default=int(os.getenv("RESEARCH_CANDIDATES_MIN_SAMPLE_DAYS", "5")))
    parser.add_argument("--no-expand", action="store_true", help="Don't expand sector themes to tickers")
    parser.add_argument("--dry-run", action="store_true", help="Print plan only")
    args = parser.parse_args()

    llm_client = LLMClient() if args.use_llm else None
    result = _generate(
        hours=args.hours,
        top_sectors=args.top_sectors,
        min_abs_net=args.min_net,
        use_llm=args.use_llm,
        llm_client=llm_client,
        max_tickers_per_sector=args.max_tickers,
        expand_tickers=not args.no_expand,
        ticker_rank=args.ticker_rank,
        baseline_days=args.baseline_days,
        min_sample_days=args.min_sample_days,
    )
    candidates = result.get("candidates", [])
    llm_analysis = result.get("llm_analysis", "")

    if args.dry_run:
        print(f"[dry-run] {len(candidates)} candidate(s) for last {args.hours}h")
        for c in candidates[:20]:
            tick = c["ticker"] or "(sektor)"
            print(f"  {c['sector']:28} {tick:8} {c['direction']:9} net={c['net_strength']:+.2f}")
        return 0

    if not candidates:
        print("No research candidates in the window (no strong macro pressure).")
        return 0

    from database.scraper_store import ScraperDatabase

    with ScraperDatabase() as store:
        saved = store.upsert_research_candidates(candidates, llm_interpretation=llm_analysis)

    print(f"Saved {saved} research candidate(s) | llm_used={result.get('llm_used', False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
