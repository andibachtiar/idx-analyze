"""Tests for Phase 26: scheduler + data-loader read cache."""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import scheduler
from ai.data_loader_pg import _cache_key, _ttl_cache

TZ = ZoneInfo("Asia/Jakarta")


class TestNextRunAt:
    def test_daily_schedule_today(self):
        now = datetime(2026, 9, 4, 10, 0, tzinfo=TZ)
        nxt = scheduler.next_run_at(now, "17:00", 24)
        assert nxt.hour == 17 and nxt.day == 4

    def test_daily_schedule_rolls_to_tomorrow(self):
        now = datetime(2026, 9, 4, 18, 0, tzinfo=TZ)
        nxt = scheduler.next_run_at(now, "17:00", 24)
        assert nxt.day == 5

    def test_interval_hours(self):
        now = datetime(2026, 9, 4, 10, 0, tzinfo=TZ)
        nxt = scheduler.next_run_at(now, None, 24)
        assert nxt > now
        assert nxt.hour in (0, 10)  # snapped to a 24h boundary


class TestTtlCache:
    def test_cache_returns_same_result_within_ttl(self):
        calls = {"n": 0}

        class Fake:
            def __init__(self):
                self._cache_ttl = 60
                self._cache = {}

            @_ttl_cache
            def load(self, key: str):
                calls["n"] += 1
                return {"key": key, "n": calls["n"]}

        fake = Fake()
        first = fake.load("a")
        second = fake.load("a")
        assert first == second
        assert calls["n"] == 1  # second call served from cache

    def test_ttl_zero_disables_cache(self):
        calls = {"n": 0}

        class Fake:
            def __init__(self):
                self._cache_ttl = 0
                self._cache = {}

            @_ttl_cache
            def load(self):
                calls["n"] += 1
                return calls["n"]

        fake = Fake()
        fake.load()
        fake.load()
        assert calls["n"] == 2

    def test_cache_key_differs_by_args(self):
        assert _cache_key("load", ("a",), {}) != _cache_key("load", ("b",), {})
