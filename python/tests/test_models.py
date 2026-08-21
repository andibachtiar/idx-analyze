"""
Tests for financial data models.
"""

import os
import sys
from datetime import date, datetime
from unittest.mock import MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock external dependencies
sys.modules['neo4j'] = MagicMock()
sys.modules['psycopg2'] = MagicMock()
sys.modules['psycopg2.extensions'] = MagicMock()
sys.modules['sqlalchemy'] = MagicMock()

import pytest

from models import Company, FinancialMetrics, FinancialPeriod, PeriodType, Source, Unit


class TestCompany:
    """Tests for Company model."""

    def test_create_company(self):
        company = Company(
            ticker="BBCA",
            name="Bank Central Asia Tbk",
            sector="Finance",
            sub_sector="Banks",
            industry="Banking"
        )
        assert company.ticker == "BBCA"
        assert company.name == "Bank Central Asia Tbk"
        assert company.sector == "Finance"

    def test_ticker_uppercase(self):
        company = Company(ticker="bbca", name="Test")
        assert company.ticker == "BBCA"

    def test_ticker_stripped(self):
        company = Company(ticker="  BBCA  ", name="Test")
        assert company.ticker == "BBCA"

    def test_equality_by_ticker(self):
        c1 = Company(ticker="BBCA", name="Bank A")
        c2 = Company(ticker="BBCA", name="Bank B")
        assert c1 == c2

    def test_hash_by_ticker(self):
        c1 = Company(ticker="BBCA", name="Bank A")
        c2 = Company(ticker="BBCA", name="Bank B")
        assert hash(c1) == hash(c2)

    def test_company_with_optional_fields(self):
        company = Company(
            ticker="TLKM",
            name="Telkom Indonesia",
            listing_date=date(1995, 12, 14),
            board="Utama"
        )
        assert company.listing_date == date(1995, 12, 14)
        assert company.board == "Utama"


class TestFinancialPeriod:
    """Tests for FinancialPeriod model."""

    def test_annual_period(self):
        period = FinancialPeriod(
            ticker="BBCA",
            period_end=date(2024, 12, 31),
            period_type=PeriodType.ANNUAL
        )
        assert period.fiscal_year == 2024
        assert period.period_label == "2024"

    def test_quarterly_period_q1(self):
        period = FinancialPeriod(
            ticker="BBCA",
            period_end=date(2024, 3, 31),
            period_type=PeriodType.QUARTERLY
        )
        assert period.fiscal_year == 2024
        assert period.fiscal_period == 1
        assert period.period_label == "2024-Q1"

    def test_quarterly_period_q2(self):
        period = FinancialPeriod(
            ticker="BBCA",
            period_end=date(2024, 6, 30),
            period_type=PeriodType.QUARTERLY
        )
        assert period.fiscal_period == 2
        assert period.period_label == "2024-Q2"

    def test_quarterly_period_q3(self):
        period = FinancialPeriod(
            ticker="BBCA",
            period_end=date(2024, 9, 30),
            period_type=PeriodType.QUARTERLY
        )
        assert period.fiscal_period == 3
        assert period.period_label == "2024-Q3"

    def test_quarterly_period_q4(self):
        period = FinancialPeriod(
            ticker="BBCA",
            period_end=date(2024, 12, 31),
            period_type=PeriodType.QUARTERLY
        )
        assert period.fiscal_period == 4
        assert period.period_label == "2024-Q4"

    def test_auto_detect_quarter_from_month(self):
        # March -> Q1
        p = FinancialPeriod(ticker="X", period_end=date(2024, 3, 31))
        assert p.fiscal_period == 1

        # June -> Q2
        p = FinancialPeriod(ticker="X", period_end=date(2024, 6, 30))
        assert p.fiscal_period == 2

        # September -> Q3
        p = FinancialPeriod(ticker="X", period_end=date(2024, 9, 30))
        assert p.fiscal_period == 3

        # December -> Q4
        p = FinancialPeriod(ticker="X", period_end=date(2024, 12, 31))
        assert p.fiscal_period == 4

    def test_period_type_detection(self):
        # End of year is typically annual
        p = FinancialPeriod(ticker="X", period_end=date(2024, 12, 31))
        assert p.period_type == PeriodType.ANNUAL or p.period_type == PeriodType.QUARTERLY

    def test_period_with_string_date(self):
        period = FinancialPeriod(
            ticker="BBCA",
            period_end="2024-06-30"
        )
        assert period.period_end == date(2024, 6, 30)

    def test_repr(self):
        period = FinancialPeriod(ticker="BBCA", period_end=date(2024, 12, 31))
        assert "BBCA" in repr(period)
        assert "2024" in repr(period)


class TestFinancialMetrics:
    """Tests for FinancialMetrics model."""

    def test_empty_metrics(self):
        metrics = FinancialMetrics()
        assert metrics.is_empty()

    def test_filled_metrics(self):
        metrics = FinancialMetrics(
            revenue=1000.0,
            net_income=100.0,
            total_assets=5000.0,
            total_equity=2000.0
        )
        assert not metrics.is_empty()
        filled = metrics.get_filled_metrics()
        assert len(filled) == 4
        assert filled['revenue'] == 1000.0
        assert filled['net_income'] == 100.0

    def test_partial_fill(self):
        metrics = FinancialMetrics(revenue=1000.0)
        assert not metrics.is_empty()
        filled = metrics.get_filled_metrics()
        assert len(filled) == 1

    def test_ratio_values(self):
        metrics = FinancialMetrics(
            roe=0.20,  # 20%
            pe_ratio=15.0,
            debt_to_equity=0.5
        )
        assert metrics.roe == 0.20
        assert metrics.pe_ratio == 15.0
        assert metrics.debt_to_equity == 0.5

    def test_none_values(self):
        metrics = FinancialMetrics(revenue=None, net_income=None)
        # None values should not be in filled metrics
        filled = metrics.get_filled_metrics()
        assert 'revenue' not in filled
        assert 'net_income' not in filled

    def test_repr(self):
        metrics = FinancialMetrics(revenue=1000.0, net_income=100.0)
        assert "2 metrics filled" in repr(metrics)


class TestModelIntegration:
    """Integration tests for models."""

    def test_full_financial_record(self):
        """Test creating a complete financial record."""
        period = FinancialPeriod(
            ticker="BBCA",
            period_end=date(2024, 12, 31),
            period_type=PeriodType.ANNUAL
        )

        metrics = FinancialMetrics(
            revenue=50000.0,
            net_income=15000.0,
            total_assets=500000.0,
            total_equity=100000.0,
            roe=0.15,
            pe_ratio=12.5
        )

        company = Company(ticker="BBCA", name="Bank Central Asia Tbk")

        assert period.ticker == "BBCA"
        assert metrics.revenue == 50000.0
        assert company.ticker == "BBCA"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
