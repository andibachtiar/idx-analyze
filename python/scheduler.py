"""
Schedule the IDX data pipeline (Phase 26).

Runs ``run_pipeline.py --all`` on a schedule and then clears the PostgreSQL
data-loader read cache so the API sees the freshly scraped data. Pure standard
library (zoneinfo + subprocess) — no Celery/Redis required.

Default behaviour (env-configurable):
  * SCRAPE_SCHEDULE_TIME  = "HH:MM" daily, interpreted in Asia/Jakarta time.
    If unset, SCRAPE_INTERVAL_HOURS is used (default 24h).

Usage:
    uv run python scheduler.py                 # start the scheduler daemon
    uv run python scheduler.py --now           # run once immediately and exit
    uv run python scheduler.py --interval 6    # override to every 6 hours
    uv run python scheduler.py --dry-run       # print next run and exit
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"
LOG_FILE = LOG_DIR / "scheduler.log"
TZ = ZoneInfo(os.environ.get("SCRAPE_TIMEZONE", "Asia/Jakarta"))


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


def next_run_at(now_local: datetime, schedule_time: str | None, interval_hours: float) -> datetime:
    """Return the next datetime (in TZ) when the pipeline should run."""
    now = now_local
    if schedule_time:
        hh, mm = schedule_time.split(":")
        candidate = datetime(now.year, now.month, now.day, int(hh), int(mm), tzinfo=TZ)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate
    step = timedelta(hours=interval_hours)
    # Snap to the last multiple of interval_hours from the epoch, then next.
    epoch = datetime(1970, 1, 1, tzinfo=TZ)
    intervals = int((now - epoch).total_seconds() // step.total_seconds()) + 1
    candidate = epoch + intervals * step
    return candidate


def run_pipeline_and_clear_cache() -> bool:
    """Run ``run_pipeline.py --all`` then clear the loader cache."""
    logging.info("Running pipeline: run_pipeline.py --all")
    try:
        result = subprocess.run(
            [sys.executable, "run_pipeline.py", "--all"],
            cwd=str(ROOT),
        )
    except Exception as exc:  # pragma: no cover
        logging.error("Pipeline launch failed: %s", exc)
        return False
    if result.returncode != 0:
        logging.error("Pipeline exited with code %s", result.returncode)
        return False
    # Invalidate the in-process API read cache so new data is served immediately.
    try:
        from ai.data_loader_pg import clear_cache
        clear_cache()
    except Exception as exc:
        logging.warning("Cache clear skipped: %s", exc)
    logging.info("Pipeline finished; read cache cleared.")
    run_auto_analyze_if_enabled()
    return True


def run_auto_analyze_if_enabled() -> None:
    """Run auto AI analysis after the data pipeline, only if enabled.

    Gated by ``AUTO_ANALYZE_ENABLED`` (true/1). ``auto_analyze.py`` itself applies
    a per-ticker recency guard (``AUTO_ANALYZE_MIN_HOURS``) so it does not spam
    the LLM when a report already exists within the guard window.
    """
    if os.environ.get("AUTO_ANALYZE_ENABLED", "").lower() not in ("1", "true"):
        return
    logging.info("Running auto-analysis (auto_analyze.py) ...")
    try:
        result = subprocess.run(
            [sys.executable, "auto_analyze.py"],
            cwd=str(ROOT),
        )
    except Exception as exc:  # pragma: no cover
        logging.error("Auto-analysis launch failed: %s", exc)
        return
    if result.returncode != 0:
        logging.error("Auto-analysis exited with code %s", result.returncode)
    else:
        logging.info("Auto-analysis finished.")


def main() -> int:
    _setup_logging()
    parser = argparse.ArgumentParser(description="Schedule the IDX data pipeline")
    parser.add_argument("--now", action="store_true", help="Run once now and exit")
    parser.add_argument("--interval", type=float, default=None, help="Override interval (hours)")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print the next run time and exit"
    )
    args = parser.parse_args()

    schedule_time = os.environ.get("SCRAPE_SCHEDULE_TIME", "")
    interval_hours = args.interval or float(os.environ.get("SCRAPE_INTERVAL_HOURS", "24"))

    if args.dry_run:
        nxt = next_run_at(datetime.now(TZ), schedule_time, interval_hours)
        print(f"Next run: {nxt.isoformat()} ({TZ})")
        return 0

    if args.now:
        print("Running pipeline once (--now)...")
        return 0 if run_pipeline_and_clear_cache() else 1

    if schedule_time:
        logging.info("Scheduler started; daily at %s (%s).", schedule_time, TZ)
    else:
        logging.info("Scheduler started; every %.0f hour(s).", interval_hours)

    while True:
        nxt = next_run_at(datetime.now(TZ), schedule_time, interval_hours)
        wait = (nxt - datetime.now(TZ)).total_seconds()
        logging.info("Next run at %s (in %.0f s). Sleeping...", nxt.isoformat(), wait)
        time.sleep(max(wait, 1.0))
        run_pipeline_and_clear_cache()


if __name__ == "__main__":
    raise SystemExit(main())
