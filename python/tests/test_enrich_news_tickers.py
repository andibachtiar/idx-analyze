"""
Tests for the news ticker enrichment module ('enrich_news_tickers').
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from enrich_news_tickers import (
    STOPWORDS,
    compile_ticker_pattern,
    extract_ticker,
)


class TestCompileTickerPattern:
    def test_matches_uppercase_ticker(self):
        pat = compile_ticker_pattern(["BBCA", "BBRI"])
        assert extract_ticker("BBCA Raup Laba", pat) == "BBCA"
        assert extract_ticker("Dividen BBRI", pat) == "BBRI"

    def test_ignores_lowercase_common_word(self):
        pat = compile_ticker_pattern(["BANK", "BBCA"])
        # 'Bank' is a stopword and lowercase; should not match
        assert extract_ticker("Bank BCA Laporan Keuangan", pat) is None

    def test_excludes_common_words_from_pattern(self):
        pat = compile_ticker_pattern(["AND", "ATM", "BBCA"])
        # None of the stopwords should be matched
        assert extract_ticker("UMKM Naik Kelas", pat) is None
        assert extract_ticker("Buka ATM malam", pat) is None
        assert extract_ticker("BBCA naik", pat) == "BBCA"

    def test_no_false_positive_for_unrelated_text(self):
        pat = compile_ticker_pattern(["SUPA", "BUMI", "EMAS"])
        assert extract_ticker("CUACA PANAS JAKARTA", pat) is None
        assert extract_ticker("Pencatatan Perdana SUPA", pat) == "SUPA"

    def test_compile_excludes_stopwords(self):
        # Ensure the compiled pattern does not contain a known stopword literal.
        pat = compile_ticker_pattern(["AND", "BANK", "BBCA"])
        pattern_str = pat.pattern
        assert "BANK" not in pattern_str
        assert "BBCA" in pattern_str

    def test_stopwords_is_a_set(self):
        assert isinstance(STOPWORDS, set)
        assert "BANK" in STOPWORDS
