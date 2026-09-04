#!/usr/bin/env python3
"""Laravel-style database CLI for the IDX-BEI project.

Usage:
    uv run python manage.py migrate
    uv run python manage.py status
    uv run python manage.py rollback
    uv run python manage.py rollback --steps 2
    uv run python manage.py reset
    uv run python manage.py fresh
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))
load_dotenv(PROJECT_DIR.parent / ".env")

from database import MigrationManager


def manager() -> MigrationManager:
    """Create a manager using DATABASE_URL from the environment."""
    return MigrationManager()


def run_command(command: str, steps: int = 1) -> None:
    db = manager()
    try:
        if command == "migrate":
            db.migrate()
        elif command == "status":
            db.status()
        elif command == "rollback":
            db.rollback(steps)
        elif command == "reset":
            db.reset()
        elif command == "fresh":
            db.fresh()
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Manage IDX-BEI PostgreSQL schema migrations"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("migrate", help="Run all pending migrations")
    subparsers.add_parser("status", help="Show migration status")

    rollback = subparsers.add_parser("rollback", help="Rollback migration batches")
    rollback.add_argument(
        "--steps",
        type=int,
        default=1,
        help="Number of migration batches to roll back (default: 1)",
    )

    subparsers.add_parser("reset", help="Rollback all applied migrations")
    subparsers.add_parser(
        "fresh", help="Drop application tables and run all migrations again"
    )

    args = parser.parse_args()
    run_command(args.command, getattr(args, "steps", 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
