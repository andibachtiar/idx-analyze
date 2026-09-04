"""Migration discovery and execution for PostgreSQL."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:  # pragma: no cover - handled when command is executed
    psycopg2 = None
    RealDictCursor = None


class MigrationManager:
    """Run and roll back Python migration modules."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL", "")
        self.migrations_dir = Path(__file__).parent
        self.connection: Any = None

    def connect(self) -> None:
        if psycopg2 is None:
            raise RuntimeError("psycopg2 is not installed; run: uv sync")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is not set")
        self.connection = psycopg2.connect(
            self.database_url,
            cursor_factory=RealDictCursor,
        )

    def close(self) -> None:
        if self.connection and not self.connection.closed:
            self.connection.close()
        self.connection = None

    def discover(self) -> list[ModuleType]:
        """Discover migrations in filename order."""
        modules = []
        for path in sorted(self.migrations_dir.glob("[0-9]*_*.py")):
            spec = importlib.util.spec_from_file_location(path.stem, path)
            if spec is None or spec.loader is None:
                raise RuntimeError(f"Cannot load migration: {path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if not hasattr(module, "name") or not hasattr(module, "up") or not hasattr(module, "down"):
                raise RuntimeError(f"Invalid migration: {path}")
            modules.append(module)
        return modules

    def _ensure_repository(self) -> None:
        """Create the migration repository without recording a migration."""
        assert self.connection is not None
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS migrations (
                    id BIGSERIAL PRIMARY KEY,
                    migration VARCHAR(255) NOT NULL UNIQUE,
                    batch INTEGER NOT NULL,
                    executed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        self.connection.commit()

    def completed(self) -> dict[str, int]:
        assert self.connection is not None
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT migration, batch FROM migrations ORDER BY id")
            return {row["migration"]: row["batch"] for row in cursor.fetchall()}

    def migrate(self) -> int:
        """Apply all pending migrations in one batch."""
        if self.connection is None:
            self.connect()
        assert self.connection is not None
        self._ensure_repository()
        completed = self.completed()
        pending = [m for m in self.discover() if m.name not in completed]
        if not pending:
            print("Nothing to migrate.")
            return 0

        batch = max(completed.values(), default=0) + 1
        for migration in pending:
            try:
                with self.connection:
                    with self.connection.cursor() as cursor:
                        migration.up(cursor)
                        cursor.execute(
                            "INSERT INTO migrations (migration, batch) VALUES (%s, %s)",
                            (migration.name, batch),
                        )
                print(f"Migrated: {migration.name}")
            except Exception:
                print(f"Migration failed: {migration.name}")
                raise
        return len(pending)

    def rollback(self, steps: int = 1) -> int:
        """Roll back the latest migration batch, or the requested number of batches."""
        if steps < 1:
            raise ValueError("steps must be at least 1")
        if self.connection is None:
            self.connect()
        assert self.connection is not None
        self._ensure_repository()
        completed = self.completed()
        if not completed:
            print("Nothing to rollback.")
            return 0

        batches = sorted(set(completed.values()), reverse=True)[:steps]
        modules = {m.name: m for m in self.discover()}
        rolled_back = 0
        for batch in batches:
            names = [name for name, value in completed.items() if value == batch]
            for name in reversed(names):
                migration = modules.get(name)
                if migration is None:
                    raise RuntimeError(f"Migration file not found: {name}")
                with self.connection:
                    with self.connection.cursor() as cursor:
                        migration.down(cursor)
                        cursor.execute("DELETE FROM migrations WHERE migration = %s", (name,))
                print(f"Rolled back: {name}")
                rolled_back += 1
        return rolled_back

    def reset(self) -> int:
        """Roll back all applied migrations."""
        if self.connection is None:
            self.connect()
        assert self.connection is not None
        self._ensure_repository()
        completed = self.completed()
        return self.rollback(len(set(completed.values()))) if completed else 0

    def fresh(self) -> int:
        """Drop application tables and run migrations from an empty database."""
        if self.connection is None:
            self.connect()
        assert self.connection is not None
        with self.connection:
            with self.connection.cursor() as cursor:
                cursor.execute("DROP TABLE IF EXISTS news_articles CASCADE")
                cursor.execute("DROP TABLE IF EXISTS stock_prices CASCADE")
                cursor.execute("DROP TABLE IF EXISTS financial_ratios CASCADE")
                cursor.execute("DROP TABLE IF EXISTS index_summaries CASCADE")
                cursor.execute("DROP TABLE IF EXISTS companies CASCADE")
                cursor.execute("DROP TABLE IF EXISTS migrations CASCADE")
        return self.migrate()

    def status(self) -> None:
        if self.connection is None:
            self.connect()
        assert self.connection is not None
        self._ensure_repository()
        completed = self.completed()
        for migration in self.discover():
            status = "Ran" if migration.name in completed else "Pending"
            batch = completed.get(migration.name, "-")
            print(f"{status:7} {batch!s:>3}  {migration.name}")
