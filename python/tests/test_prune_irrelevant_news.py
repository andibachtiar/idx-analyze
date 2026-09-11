"""Tests for the irrelevant-news cleanup (backlog #3)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import prune_irrelevant_news as p


class _Connection:
    def __init__(self, rows):
        self.committed = False
        self._cursor = _Cursor(rows)

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True


class _Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.rowcount = 0
        self.deleted_params = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        if sql.strip().upper().startswith("DELETE"):
            self.deleted_params = params
            self.rowcount = len(params[0]) if params else 0

    def fetchall(self):
        return self.rows


class _Store:
    def __init__(self, rows):
        self.connection = _Connection(rows)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def _ensure_connection(self):
        pass

    def cursor(self):
        return self.connection.cursor()

    @property
    def cursor_obj(self):
        return self.connection._cursor


def _rows():
    # (id, ticker, title, content, company name)
    return [
        (1, "SICO", "Mengapa saham Sigma Lithium turun hari ini?", "", "Sigma Energy Compressindo"),
        (2, "SICO", "SICO raih kontrak baru", "Sigma Energy Compressindo ekspansi", "Sigma Energy Compressindo"),
        (3, "BBRI", "BRI Perkuat Kontribusi bagi Ekonomi Nasional", "", "Bank Rakyat Indonesia (Persero) Tbk."),
    ]


class TestFindIrrelevantNews:
    def test_flags_only_the_unrelated_row(self):
        flagged = p.find_irrelevant_news(_Store(_rows()))
        assert flagged == [(1, "SICO", "Mengapa saham Sigma Lithium turun hari ini?")]

    def test_keeps_genuine_rows(self):
        flagged_ids = {row[0] for row in p.find_irrelevant_news(_Store(_rows()))}
        assert 2 not in flagged_ids  # mentions SICO
        assert 3 not in flagged_ids  # mentions the BRI acronym


class TestPrune:
    def test_dry_run_does_not_delete(self, monkeypatch):
        store = _Store(_rows())
        monkeypatch.setattr(p, "ScraperDatabase", lambda: store)
        result = p.prune_irrelevant_news(apply=False)
        assert result == {"irrelevant": 1, "deleted": 0}
        assert store.cursor_obj.deleted_params is None
        assert store.connection.committed is False

    def test_apply_deletes_flagged_rows(self, monkeypatch):
        store = _Store(_rows())
        monkeypatch.setattr(p, "ScraperDatabase", lambda: store)
        result = p.prune_irrelevant_news(apply=True)
        assert result == {"irrelevant": 1, "deleted": 1}
        assert store.cursor_obj.deleted_params == ([1],)
        assert store.connection.committed is True

    def test_noop_when_everything_is_relevant(self, monkeypatch):
        store = _Store([_rows()[1]])
        monkeypatch.setattr(p, "ScraperDatabase", lambda: store)
        assert p.prune_irrelevant_news(apply=True) == {"irrelevant": 0, "deleted": 0}
