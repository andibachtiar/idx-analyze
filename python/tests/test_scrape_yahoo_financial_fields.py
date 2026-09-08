"""
Tests for the yfinance enrichment/scraper ('scrape_yahoo_financial_fields').
Covers ticker conversion and CAGR computation from a mock financials frame.
"""

from __future__ import annotations

import os
import re
import sys
from unittest.mock import MagicMock, patch

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import scrape_yahoo_financial_fields as scrub


class TestTickerConversion:
    def test_normalize_adds_jk(self):
        assert scrub.normalize_yf_ticker("BBCA") == "BBCA.JK"

    def test_normalize_preserves_jk(self):
        assert scrub.normalize_yf_ticker("BBCA.JK") == "BBCA.JK"

    def test_to_idx_strips_jk(self):
        assert scrub.to_idx_ticker("BBCA.JK") == "BBCA"


class TestComputeCagr:
    def _frame(self, values):
        """yfinance financials: index = metric rows, columns = periods newest-first."""
        cols = [f"FY{len(values) - i}" for i in range(len(values))]
        return pd.DataFrame(
            [values],
            columns=cols,
            index=pd.Index(["Total Revenue"]),
        )

    def test_cagr_over_multiple_years(self):
        # 100 (oldest) -> 121 over 2 periods => (121/100)^(1/2)-1 = 0.10
        frame = self._frame([121.0, 110.0, 100.0])  # newest -> oldest
        assert abs(scrub.compute_cagr(frame, "Total Revenue") - 0.10) < 1e-6

    def test_cagr_returns_none_when_insufficient(self):
        frame = self._frame([100.0])
        assert scrub.compute_cagr(frame, "Total Revenue") is None

    def test_cagr_returns_none_for_nonpositive(self):
        frame = self._frame([100.0, -50.0, -100.0])
        assert scrub.compute_cagr(frame, "Total Revenue") is None

    def test_cagr_returns_none_when_row_missing(self):
        empty = pd.DataFrame(index=pd.Index(["Net Income"]))
        assert scrub.compute_cagr(empty, "Total Revenue") is None

    def test_cagr_skips_nan(self):
        # NaN treated as missing; still 2 real values -> usable CAGR
        frame = self._frame([121.0, float("nan"), 100.0])
        assert abs(scrub.compute_cagr(frame, "Total Revenue") - 0.10) < 1e-6


class TestFetchEnrichment:
    def test_computes_growth_from_financials(self):
        ticker = MagicMock()
        ticker.info = {
            "dividendYield": 0.05,
            "currentRatio": 2.0,
            "payoutRatio": 0.7,
        }
        financials = pd.DataFrame(
            {"2025-12-31": [121.0], "2024-12-31": [110.0], "2023-12-31": [100.0]},
            index=pd.Index(["Total Revenue"]),
        )
        # Add Net Income row too
        financials.loc["Net Income"] = [120.0, 100.0, 80.0]
        financials.loc["Diluted EPS"] = [8.08, 7.4, 6.7]
        ticker.financials = financials
        with patch("scrape_yahoo_financial_fields.yf.Ticker", return_value=ticker):
            rec = scrub.fetch_enrichment("BBCA.JK")
        assert rec is not None
        assert rec["ticker"] == "BBCA"
        assert abs(rec["revenue_cagr"] - 0.10) < 1e-6  # (121/100)^(1/2)-1
        assert abs(rec["earnings_cagr"] - 0.224744871) < 1e-5
        # (8.08/6.7)^(1/2)-1
        assert abs(rec["eps_cagr"] - ((8.08 / 6.7) ** 0.5 - 1.0)) < 1e-6
        # dividend_yield is returned raw (fraction); store converts to percent
        assert abs(rec["dividend_yield"] - 0.05) < 1e-6

    def test_returns_none_when_no_values(self):
        ticker = MagicMock()
        ticker.info = {}
        ticker.financials = None
        with patch("scrape_yahoo_financial_fields.yf.Ticker", return_value=ticker):
            assert scrub.fetch_enrichment("BBCA.JK") is None
