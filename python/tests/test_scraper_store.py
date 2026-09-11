"""Unit tests for the financial_ratios upsert helpers.

Regression guard for the non-idempotent upsert: ``fiscal_period`` is NULL for
all IDX annual rows, so the old UNIQUE (ticker, fiscal_year, fiscal_period)
never fired and every pipeline run inserted another copy (up to 6 per period).
The fix is the NULL-correct unique expression index created by migration
``202609100020_fix_financial_ratios_dedup``, matched here by the conflict
target, a NULL-safe DO UPDATE SET and in-batch deduplication.
"""

import importlib.util
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.scraper_store import (  # noqa: E402
    _FINANCIAL_RATIO_COLUMNS,
    _FINANCIAL_RATIO_CONFLICT,
    _FINANCIAL_RATIO_KEY,
    _date,
    _dedupe_ratio_rows,
    _financial_ratio_update_assignments,
    _period_from_date,
)

_INDEX = {name: position for position, name in enumerate(_FINANCIAL_RATIO_COLUMNS)}


def _row(**values):
    """Build a financial_ratios row tuple from named column values."""
    unknown = set(values) - set(_FINANCIAL_RATIO_COLUMNS)
    assert not unknown, f"unknown columns: {unknown}"
    row = [None] * len(_FINANCIAL_RATIO_COLUMNS)
    for name, value in values.items():
        row[_INDEX[name]] = value
    return tuple(row)


def _value(row, name):
    return row[_INDEX[name]]


def test_dedupe_merges_complementary_columns():
    """Duplicates held complementary data (enrichment vs operating_income)."""
    enriched = _row(
        ticker="SICO", fiscal_year=2024, period_end="2024-09-30",
        current_ratio=7.21, dividend_yield=4.35,
    )
    scoring = _row(
        ticker="SICO", fiscal_year=2024, period_end="2024-09-30",
        operating_income=11.07,
    )

    merged = _dedupe_ratio_rows([enriched, scoring])

    assert len(merged) == 1
    assert _value(merged[0], "current_ratio") == 7.21
    assert _value(merged[0], "dividend_yield") == 4.35
    assert _value(merged[0], "operating_income") == 11.07


def test_dedupe_last_non_null_value_wins():
    older = _row(ticker="X", fiscal_year=2024, period_end="2024-12-31", revenue=1.0, roe=5.0)
    newer = _row(ticker="X", fiscal_year=2024, period_end="2024-12-31", revenue=None, eps=2.0)

    merged = _dedupe_ratio_rows([older, newer])

    assert len(merged) == 1
    # NULL in the newer row must not clobber the older non-NULL value...
    assert _value(merged[0], "revenue") == 1.0
    assert _value(merged[0], "roe") == 5.0
    # ...while a newer non-NULL value does win.
    assert _value(merged[0], "eps") == 2.0


def test_dedupe_treats_null_and_zero_fiscal_period_as_same_key():
    """Matches the COALESCE(fiscal_period, 0) conflict index."""
    null_period = _row(ticker="X", fiscal_year=2024, period_end="2024-12-31", revenue=1.0)
    zero_period = _row(
        ticker="X", fiscal_year=2024, fiscal_period=0, period_end="2024-12-31", eps=3.0
    )

    merged = _dedupe_ratio_rows([null_period, zero_period])

    assert len(merged) == 1
    assert _value(merged[0], "revenue") == 1.0
    assert _value(merged[0], "eps") == 3.0


def test_dedupe_keeps_distinct_period_end_separate():
    """One (ticker, fiscal_year) can legitimately have two period ends (BLOG 2024)."""
    q1 = _row(ticker="BLOG", fiscal_year=2024, period_end="2024-03-31", revenue=10.0)
    q4 = _row(ticker="BLOG", fiscal_year=2024, period_end="2024-12-31", revenue=40.0)

    merged = _dedupe_ratio_rows([q1, q4])

    assert len(merged) == 2


def test_dedupe_keeps_distinct_tickers_separate():
    a = _row(ticker="AAA", fiscal_year=2024, period_end="2024-12-31", revenue=1.0)
    b = _row(ticker="BBB", fiscal_year=2024, period_end="2024-12-31", revenue=2.0)

    assert len(_dedupe_ratio_rows([a, b])) == 2


def test_dedupe_preserves_first_seen_order():
    first = _row(ticker="BBB", fiscal_year=2024, period_end="2024-12-31", revenue=1.0)
    second = _row(ticker="AAA", fiscal_year=2024, period_end="2024-12-31", revenue=2.0)

    merged = _dedupe_ratio_rows([first, second])

    assert [_value(r, "ticker") for r in merged] == ["BBB", "AAA"]


def test_dedupe_leaves_single_row_untouched():
    row = _row(ticker="X", fiscal_year=2024, period_end="2024-12-31", revenue=1.0)

    assert _dedupe_ratio_rows([row]) == [row]


def test_columns_are_unique():
    assert len(_FINANCIAL_RATIO_COLUMNS) == len(set(_FINANCIAL_RATIO_COLUMNS))


def test_period_from_date_quarterly_and_annual():
    # Mar / Jun / Sep -> Q1 / Q2 / Q3
    assert _period_from_date(_date("2024-03-31")) == 1
    assert _period_from_date(_date("2024-06-30")) == 2
    assert _period_from_date(_date("2024-09-30")) == 3
    # December is the full fiscal year (annual) -> None
    assert _period_from_date(_date("2024-12-31")) is None


def test_period_from_date_none_inputs():
    assert _period_from_date(None) is None
    assert _period_from_date(_date("not-a-date")) is None


def test_conflict_target_covers_the_unique_key():
    assert _FINANCIAL_RATIO_KEY == {
        "ticker", "fiscal_year", "fiscal_period", "period_end"
    }
    for column in ("ticker", "fiscal_year", "period_end"):
        assert column in _FINANCIAL_RATIO_CONFLICT
    # fiscal_period must be COALESCEd, not a bare column.
    assert "COALESCE(fiscal_period, 0)" in _FINANCIAL_RATIO_CONFLICT


def test_update_assignments_are_null_safe_and_skip_key_columns():
    assignments = _financial_ratio_update_assignments()
    settable = [
        c for c in _FINANCIAL_RATIO_COLUMNS if c not in _FINANCIAL_RATIO_KEY and c != "source"
    ]
    for column in settable:
        assert f"{column} = COALESCE(EXCLUDED.{column}, financial_ratios.{column})" in assignments
    for column in _FINANCIAL_RATIO_KEY | {"source"}:
        assert f"{column} = " not in assignments


def _load_migration():
    path = os.path.join(
        os.path.dirname(__file__),
        "..", "database", "202609100020_fix_financial_ratios_dedup.py",
    )
    spec = importlib.util.spec_from_file_location("fix_financial_ratios_dedup", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_excludes_managed_columns_from_merge():
    migration = _load_migration()
    assert {
        "id", "ticker", "fiscal_year", "fiscal_period", "period_end",
        "source", "created_at", "updated_at",
    } == migration._EXCLUDED


def test_migration_data_columns_use_column_name_keys():
    """Migration runner uses RealDictCursor, so rows are dict-like."""
    migration = _load_migration()

    class FakeCursor:
        def __init__(self):
            self.rows = [
                {"column_name": "id"},
                {"column_name": "ticker"},
                {"column_name": "revenue"},
                {"column_name": "roe"},
                {"column_name": "updated_at"},
            ]

        def execute(self, *args, **kwargs):
            pass

        def fetchall(self):
            return self.rows

    assert migration._data_columns(FakeCursor()) == ["revenue", "roe"]


def test_migration_metadata():
    migration = _load_migration()
    assert migration.name == "202609100020_fix_financial_ratios_dedup"
    assert callable(migration.up) and callable(migration.down)


def _load_fiscal_period_migration():
    path = os.path.join(
        os.path.dirname(__file__),
        "..", "database", "202609100021_backfill_fiscal_period.py",
    )
    spec = importlib.util.spec_from_file_location("backfill_fiscal_period", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fiscal_period_backfill_migration_metadata():
    migration = _load_fiscal_period_migration()
    assert migration.name == "202609100021_backfill_fiscal_period"
    assert callable(migration.up) and callable(migration.down)
