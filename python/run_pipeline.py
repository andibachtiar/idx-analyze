"""
Data Pipeline Orchestrator (Phase 24).

Runs the persistence scrapers in dependency order from a single command, with
retry/backoff, structured logging, and a failure ledger. Each step is a CLI
script executed via ``sys.executable`` so it behaves exactly like running it by
hand while letting one command drive the full ingestion flow.

Usage:
    uv run python run_pipeline.py --all               # run every step in order
    uv run python run_pipeline.py --steps prices,news # run a subset
    uv run python run_pipeline.py --steps yfinance --backfill
    uv run python run_pipeline.py --steps all --retries 3 --delay 1.0
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "data" / "pipeline_ledger.jsonl"
LOG_DIR = ROOT / "logs"
LOG_FILE = LOG_DIR / "pipeline.log"

# Ordered so foreign-key dependencies (companies) are populated before prices,
# financials, and news.
STEPS: list[dict[str, object]] = [
    {
        "name": "companies",
        "script": "scrape_company_profiles.py",
        "args": [],
        "desc": "Company master list + details (universe for FKs)",
    },
    {
        "name": "prices",
        "script": "scrape_stock_prices.py",
        "args": [],
        "desc": "Daily OHLCV prices (incremental; only missing dates)",
    },
    {
        "name": "financial_ratio",
        "script": "scrape_financial_ratio.py",
        "args": [],
        "desc": "Latest IDX financial ratios",
    },
    {
        "name": "yfinance",
        "script": "scrape_yahoo_financial_fields.py",
        "args": [],
        "desc": "Enrichment: dividend_yield / current_ratio / payout_ratio / CAGR",
    },
    {
        "name": "financial_history",
        "script": "backfill_financial_history.py",
        "args": [],
        "desc": "Multi-year financial history from yfinance (added for fundamentals chart)",
    },
    {
        "name": "news",
        "script": "scrape_idx_news.py",
        "args": [],
        "desc": "IDX news feed (uses real NewsCode for dedup)",
    },
    {
        "name": "news_link",
        "script": "enrich_news_tickers.py",
        "args": [],
        "desc": "Link news articles to known IDX tickers",
    },
    {
        "name": "company_news",
        "script": "scrape_company_news.py",
        "args": [],
        "desc": "Per-ticker Yahoo Finance news (deterministic dedup key)",
    },
    {
        "name": "news_brave",
        "script": "scrape_brave_news.py",
        "args": ["--macro"],
        "desc": "Brave macro/economy/politics queries (ticker=NULL, source-filtered)",
    },
    {
        "name": "news_impacts",
        "script": "enrich_news_impacts.py",
        "args": [],
        "desc": "Deterministic news -> sector/ticker impact tags (B3)",
    },
    {
        "name": "research_candidates",
        "script": "generate_research_candidates.py",
        "args": [],
        "desc": "Deterministic macro -> research candidates + optional LLM interpretation (B5)",
    },
]


def _setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def _ledger(record: dict) -> None:
    appending = not LEDGER.exists()
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as fh:
        if appending:
            fh.write("{\"run_started_at\": \"-\"}\n")
        fh.write(json.dumps(record, default=str) + "\n")


def run_step(step: dict, retries: int, delay: float) -> bool:
    name = str(step["name"])
    script = str(step["script"])
    start = time.perf_counter()
    attempt = 0
    last_err = ""
    while attempt <= retries:
        attempt += 1
        cmd = [sys.executable, script, *[str(a) for a in step.get("args", [])]]
        output_tail = []
        try:
            # Stream the scraper's output live so the user sees progress instead
            # of a silent wait; keep the tail for the failure ledger.
            proc = subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                print(line, end="", flush=True)
                output_tail.append(line)
                if len(output_tail) > 40:
                    output_tail.pop(0)
            proc.wait()
            tail_text = "".join(output_tail)[-600:]
            if proc.returncode == 0:
                _ledger({
                    "ts": datetime.now(UTC).isoformat(),
                    "step": name,
                    "status": "ok",
                    "attempts": attempt,
                    "seconds": round(time.perf_counter() - start, 2),
                })
                logging.info("OK   %-16s (%ds)", name, round(time.perf_counter() - start, 2))
                return True
            last_err = tail_text or f"exit code {proc.returncode}"
            logging.warning("retry step=%s attempt=%d", name, attempt)
        except Exception as exc:  # pragma: no cover - subprocess failure
            last_err = str(exc)
            logging.warning("error step=%s attempt=%d: %s", name, attempt, exc)
        if attempt <= retries:
            time.sleep(delay * attempt)
    _ledger({
        "ts": datetime.now(UTC).isoformat(),
        "step": name,
        "status": "failed",
        "attempts": attempt,
        "seconds": round(time.perf_counter() - start, 2),
        "error": last_err,
    })
    logging.error("FAIL %-16s after %d attempt(s): %s", name, attempt, last_err.strip())
    return False


def select_steps(steps_arg: str | None) -> tuple[list[dict], list[str]]:
    """Return (selected_steps, unknown_names) for a comma-separated --steps value.

    ``None`` or empty means all steps; unknown names are returned so the caller
    can report them instead of silently ignoring typos.
    """
    if not steps_arg:
        return list(STEPS), []
    wanted = {s.strip() for s in steps_arg.lower().split(",") if s.strip()}
    selected = [s for s in STEPS if str(s["name"]) in wanted]
    unknown = sorted(wanted - {str(s["name"]) for s in selected})
    return selected, unknown


def main() -> int:
    _setup_logging()
    parser = argparse.ArgumentParser(description="Run the IDX data pipeline in order")
    parser.add_argument("--all", action="store_true", help="Run every step in order")
    parser.add_argument(
        "--steps",
        help="Comma-separated subset of step names (e.g. 'prices,news')",
    )
    parser.add_argument("--retries", type=int, default=2, help="Retries per failed step")
    parser.add_argument("--delay", type=float, default=1.0, help="Base backoff delay (seconds)")
    parser.add_argument("--backfill", action="store_true", help="Scrape 5y price history each run")
    args = parser.parse_args()

    if not args.all and not args.steps:
        parser.error("Provide --all or --steps")

    if args.steps:
        selected, unknown = select_steps(args.steps)
        if unknown:
            print(f"Unknown step(s): {', '.join(unknown)}")
            return 1
    else:
        selected = list(STEPS)

    if args.backfill:
        for s in selected:
            if str(s["name"]) == "prices":
                s["args"] = ["--backfill"]
            if str(s["name"]) == "financial_history":
                s["args"] = []

    print("=" * 66)
    print("IDX DATA PIPELINE")
    print("=" * 66)
    failures = []
    for step in selected:
        print(f"\n→ {step['name']} — {step['desc']}")
        ok = run_step(step, args.retries, args.delay)
        if not ok:
            failures.append(step["name"])
    print("\n" + "=" * 66)
    if failures:
        print(f"Pipeline finished with {len(failures)} failed step(s): {', '.join(failures)}")
        return 1
    print("Pipeline finished successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
